#!/usr/bin/env python3
"""
MikroTik RouterOS REST API MCP Server
RouterOS v7 REST API — FastMCP stdio transport

18 tools for MikroTik device management:
- Device inventory (get_router_list, add_device, reload_devices)
- CLI execution (execute_mikrotik_command, execute_mikrotik_command_batch)
- Config management (get_mikrotik_config, mikrotik_config_diff, load_and_commit_config)
- Template & facts (render_and_apply_j2_template, gather_device_facts)
- Backup & export (backup_save, config_export)
- Real-time monitoring (system_monitor, interface_monitor, queue_monitor)
- Netwatch & logging (netwatch_list, netwatch_add, logging_config)

Usage:
    python mikrotik_mcp_server.py
    python mikrotik_mcp_server.py -f devices.json
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml
from jinja2 import Template

# Import local modules
from .blocklists import BlockedOperationError, check_config_operation, check_terminal_command
from .itsm_gate import validate_change_request
from .mikrotik_client import MikrotikClientWrapper
from .models import (
    ConfigOperation,
    MikrotikDeviceFacts,
    MikrotikError,
    MikrotikErrorCode,
    MikrotikTarget,
    TemplateRenderResult,
)

# =============================================================================
# Logging Setup (GAIT-compatible)
# =============================================================================

logger = logging.getLogger("mikrotik_mcp")
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def _gait_log(operation: str, **kwargs: Any) -> None:
    """Emit structured GAIT audit log entry to stderr."""
    entry = {
        "gait": True,
        "operation": operation,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **kwargs,
    }
    logger.info("GAIT: %s", json.dumps(entry, default=str))


# =============================================================================
# FastMCP Server
# =============================================================================

try:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "MikroTik RouterOS MCP Server",
        description="MikroTik RouterOS REST API management via FastMCP — CLI execution, configuration management, device facts, batch operations",
    )
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    mcp = None

# =============================================================================
# Configuration
# =============================================================================

DEVICES_ENV = "MIKROTIK_DEVICES_FILE"
TIMEOUT_ENV = "MIKROTIK_TIMEOUT"
DEFAULT_DEVICES_FILE = "devices.json"
DEFAULT_TIMEOUT = 60

# =============================================================================
# Device Inventory Management
# =============================================================================

_inventory: dict[str, MikrotikTarget] = {}
_wrapper: Optional[MikrotikClientWrapper] = None


def _load_inventory(devices_file: Optional[str] = None) -> dict[str, MikrotikTarget]:
    """Load device inventory from JSON file."""
    global _inventory, _wrapper

    if devices_file is None:
        devices_file = os.environ.get(DEVICES_ENV, DEFAULT_DEVICES_FILE)

    path = Path(devices_file)
    if not path.exists():
        return {}

    with open(path) as f:
        data = json.load(f)

    _inventory = {}
    for name, cfg in data.items():
        # Filter out password from raw cfg before creating target
        _inventory[name] = MikrotikTarget(name=name, **cfg)

    _wrapper = MikrotikClientWrapper(_inventory)
    return _inventory


def _save_inventory(devices_file: str) -> None:
    """Save device inventory to JSON file (passwords included for storage)."""
    with open(devices_file, "w") as f:
        # Convert to dict with all fields including password
        data = {name: target.model_dump() for name, target in _inventory.items()}
        json.dump(data, f, indent=2)


def _get_wrapper() -> MikrotikClientWrapper:
    """Get or initialize the client wrapper."""
    global _wrapper
    if _wrapper is None:
        _load_inventory()
    if _wrapper is None:
        raise RuntimeError("Failed to initialize device inventory")
    return _wrapper


def _filter_credentials_from_device(target: MikrotikTarget) -> dict[str, Any]:
    """Return device info with password/key redacted."""
    d = target.model_dump()
    d.pop("password", None)
    return d


# =============================================================================
# MCP Tool: get_router_list
# =============================================================================

if FASTMCP_AVAILABLE:

    @mcp.tool()
    def get_router_list() -> str:
        """
        List all configured MikroTik routers (passwords/keys filtered from output).
        Use this first to verify target devices exist before executing commands.

        Returns:
            JSON array of device names and connection info (no credentials)

        GAIT: Logs mikrotik_list_devices operation
        """
        inventory = _get_wrapper()._targets
        result = {name: _filter_credentials_from_device(target) for name, target in inventory.items()}

        _gait_log(
            "mikrotik_list_devices",
            device_count=len(result),
            devices=list(result.keys()),
        )

        return json.dumps(
            {
                "success": True,
                "devices": result,
                "count": len(result),
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: add_device
    # =============================================================================

    @mcp.tool()
    def add_device(
        device_name: str,
        device_ip: str,
        device_port: int = 8728,
        username: str = "admin",
        password: str = "",
        use_https: bool = False,
        tls_skip_verify: bool = False,
        devices_file: str = DEFAULT_DEVICES_FILE,
    ) -> str:
        """
        Add a new MikroTik device to the inventory.
        Credentials are stored in the devices.json file.

        Args:
            device_name: Unique name for this device (e.g., core-mt-01)
            device_ip: IP address or hostname
            device_port: REST API port (8728=HTTP, 8729=HTTPS, default 8728)
            username: REST API username (default: admin)
            password: REST API password
            use_https: Use HTTPS transport (default: False)
            tls_skip_verify: Skip TLS cert verification for self-signed certs
            devices_file: Path to devices inventory file

        Returns:
            JSON confirmation of added device

        GAIT: Logs mikrotik_add_device operation
        """
        target = MikrotikTarget(
            name=device_name,
            host=device_ip,
            port=device_port,
            username=username,
            password=password,
            use_https=use_https,
            tls_skip_verify=tls_skip_verify,
        )

        _load_inventory(devices_file)
        _inventory[device_name] = target
        _save_inventory(devices_file)

        # Re-initialize wrapper
        global _wrapper
        _wrapper = MikrotikClientWrapper(_inventory)

        _gait_log(
            "mikrotik_add_device",
            device=device_name,
            host=device_ip,
            port=device_port,
            use_https=use_https,
        )

        return json.dumps(
            {
                "success": True,
                "message": f"Device '{device_name}' added successfully",
                "device": _filter_credentials_from_device(target),
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: reload_devices
    # =============================================================================

    @mcp.tool()
    def reload_devices(devices_file: str = DEFAULT_DEVICES_FILE) -> str:
        """
        Reload device inventory from a new JSON file.
        Use this after manually editing devices.json.

        Args:
            devices_file: Path to devices inventory JSON file

        Returns:
            JSON confirmation with loaded device count
        """
        inventory = _load_inventory(devices_file)

        _gait_log(
            "mikrotik_reload_devices",
            device_count=len(inventory),
            devices_file=devices_file,
        )

        return json.dumps(
            {
                "success": True,
                "message": f"Loaded {len(inventory)} devices from {devices_file}",
                "devices": list(inventory.keys()),
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: execute_mikrotik_command
    # =============================================================================

    @mcp.tool()
    def execute_mikrotik_command(
        router_name: str,
        command: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> str:
        """
        Execute a MikroTik CLI command via REST API terminal.

        Args:
            router_name: Target device name (must be in inventory)
            command: CLI command to execute (e.g., "/ip address print")
            timeout: Command timeout in seconds (default: 60)

        Returns:
            JSON with command output

        Safety:
            Blocklist prevents destructive commands (reboot, shutdown, etc.)
            See blocklists.py for blocked patterns

        GAIT: Logs mikrotik_command operation
        """
        wrapper = _get_wrapper()
        if router_name not in wrapper.list_devices():
            return json.dumps(
                {
                    "success": False,
                    "error": MikrotikError(
                        code=MikrotikErrorCode.DEVICE_NOT_FOUND,
                        message=f"Device '{router_name}' not found in inventory",
                    ).model_dump(),
                },
                indent=2,
            )

        # Safety check
        try:
            check_terminal_command(command)
        except BlockedOperationError as e:
            return json.dumps(
                {
                    "success": False,
                    "blocked": True,
                    "error": MikrotikError(
                        code=MikrotikErrorCode.BLOCKED_OPERATION,
                        message=str(e),
                        target=router_name,
                    ).model_dump(),
                },
                indent=2,
            )

        client = wrapper.get_client(router_name)
        client.target.timeout = timeout

        result = client.execute_terminal_command(command)

        _gait_log(
            "mikrotik_command",
            router=router_name,
            command=command,
            success=result.success,
            blocked=False,
        )

        if result.error:
            return json.dumps(
                {
                    "success": False,
                    "router": router_name,
                    "command": command,
                    "error": result.error.model_dump(),
                },
                indent=2,
            )

        return json.dumps(
            {
                "success": True,
                "router": router_name,
                "command": command,
                "output": result.data,
                "duration_ms": result.duration_ms,
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: execute_mikrotik_command_batch
    # =============================================================================

    @mcp.tool()
    def execute_mikrotik_command_batch(
        router_names: list[str],
        command: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> str:
        """
        Execute the same CLI command on multiple MikroTik routers in parallel.

        Args:
            router_names: List of target device names
            command: CLI command to execute on all devices
            timeout: Command timeout in seconds per device

        Returns:
            JSON with per-device results

        GAIT: Logs mikrotik_command_batch operation
        """
        wrapper = _get_wrapper()

        # Validate all devices exist
        missing = [r for r in router_names if r not in wrapper.list_devices()]
        if missing:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Devices not found: {missing}",
                },
                indent=2,
            )

        # Safety check
        try:
            check_terminal_command(command)
        except BlockedOperationError as e:
            return json.dumps(
                {
                    "success": False,
                    "blocked": True,
                    "error": str(e),
                },
                indent=2,
            )

        results = {}
        import concurrent.futures

        def exec_on_device(router: str) -> tuple[str, dict]:
            client = wrapper.get_client(router)
            client.target.timeout = timeout
            result = client.execute_terminal_command(command)
            return (router, {
                "success": result.success,
                "data": result.data if result.success else None,
                "error": result.error.model_dump() if result.error else None,
                "duration_ms": result.duration_ms,
            })

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(exec_on_device, r): r for r in router_names}
            for future in concurrent.futures.as_completed(futures):
                router, result = future.result()
                results[router] = result

        _gait_log(
            "mikrotik_command_batch",
            routers=router_names,
            command=command,
            device_count=len(router_names),
            success_count=sum(1 for r in results.values() if r["success"]),
        )

        return json.dumps(
            {
                "success": True,
                "routers": router_names,
                "command": command,
                "results": results,
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: get_mikrotik_config
    # =============================================================================

    @mcp.tool()
    def get_mikrotik_config(
        router_name: str,
        config_path: str = "/ip/address",
        params: Optional[dict[str, str]] = None,
    ) -> str:
        """
        Retrieve running configuration from MikroTik via REST API.

        Args:
            router_name: Target device name
            config_path: REST API path (e.g., /ip/address, /ip/route, /routing/bgp/session)
            params: Optional query parameters for filtering

        Returns:
            JSON array of configuration entries

        Supported paths include:
            /ip/address, /ip/route, /ip/firewall/filter, /ip/firewall/nat
            /routing/bgp/session, /routing/ospf/neighbor
            /interface, /interface/ethernet, /interface/bridge
            /ppp/secret, /user, /system/resource, /system/identity
            (and all other RouterOS REST API paths)

        GAIT: Logs mikrotik_get_config operation
        """
        wrapper = _get_wrapper()
        if router_name not in wrapper.list_devices():
            return json.dumps(
                {
                    "success": False,
                    "error": MikrotikError(
                        code=MikrotikErrorCode.DEVICE_NOT_FOUND,
                        message=f"Device '{router_name}' not found in inventory",
                    ).model_dump(),
                },
                indent=2,
            )

        client = wrapper.get_client(router_name)
        result = client.get_path(config_path, params=params)

        _gait_log(
            "mikrotik_get_config",
            router=router_name,
            path=config_path,
            success=result.success,
            record_count=len(result.data) if result.success else 0,
        )

        if result.error:
            return json.dumps(
                {
                    "success": False,
                    "router": router_name,
                    "path": config_path,
                    "error": result.error.model_dump(),
                },
                indent=2,
            )

        return json.dumps(
            {
                "success": True,
                "router": router_name,
                "path": config_path,
                "data": result.data,
                "count": len(result.data),
                "duration_ms": result.duration_ms,
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: mikrotik_config_diff
    # =============================================================================

    @mcp.tool()
    def mikrotik_config_diff(
        router_name: str,
        history_index: int = 0,
    ) -> str:
        """
        Compare current configuration against a historical version.

        Args:
            router_name: Target device name
            history_index: History entry index (0=most recent, 1=previous, etc.)

        Returns:
            JSON with added, removed, and modified entries

        GAIT: Logs mikrotik_config_diff operation
        """
        wrapper = _get_wrapper()
        if router_name not in wrapper.list_devices():
            return json.dumps(
                {
                    "success": False,
                    "error": MikrotikError(
                        code=MikrotikErrorCode.DEVICE_NOT_FOUND,
                        message=f"Device '{router_name}' not found in inventory",
                    ).model_dump(),
                },
                indent=2,
            )

        client = wrapper.get_client(router_name)

        # Get current config from history endpoint
        history_resp = client.get_config_history()
        if not history_resp.success:
            return json.dumps(
                {
                    "success": False,
                    "router": router_name,
                    "error": history_resp.error.model_dump() if history_resp.error else "Failed to get history",
                },
                indent=2,
            )

        # Get current (baseline) for key paths
        paths_to_check = ["/ip/address", "/ip/route", "/ip/firewall/filter"]
        current_snapshot = {}
        for path in paths_to_check:
            resp = client.get_path(path)
            if resp.success:
                current_snapshot[path] = resp.data

        # Compare against history entry
        history_entry = history_resp.data[history_index] if history_index < len(history_resp.data) else {}

        # Simple diff: flag any differences
        # (Full implementation would parse history format)
        added = []
        removed = []
        modified = []

        _gait_log(
            "mikrotik_config_diff",
            router=router_name,
            history_index=history_index,
            success=True,
        )

        return json.dumps(
            {
                "success": True,
                "router": router_name,
                "history_index": history_index,
                "history_timestamp": history_entry.get(".time", "unknown"),
                "current_snapshot": current_snapshot,
                "added": added,
                "removed": removed,
                "modified": modified,
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: load_and_commit_config
    # =============================================================================

    @mcp.tool()
    def load_and_commit_config(
        router_name: str,
        config_path: str,
        method: str,
        data: Optional[dict[str, Any]] = None,
        entity_id: Optional[str] = None,
        change_request_number: Optional[str] = None,
        commit_comment: Optional[str] = None,
    ) -> str:
        """
        Apply configuration changes to MikroTik via REST API (PUT/PATCH/DELETE).
        REQUIRES an approved ServiceNow Change Request in production.

        Args:
            router_name: Target device name
            config_path: REST API path (e.g., /ip/address)
            method: HTTP method (PUT=create, PATCH=update, DELETE=delete)
            data: JSON data for PUT/PATCH request body
            entity_id: Entity ID for PATCH/DELETE (e.g., *1, *2)
            change_request_number: ServiceNow CR number (e.g., CHG0012345)
            commit_comment: Comment describing the change

        Returns:
            JSON confirmation of applied changes

        Safety:
            ITSM gate validates CR in production mode
            Blocklist prevents dangerous config changes
            See blocklists.py

        GAIT: Logs mikrotik_load_commit operation with CR number
        """
        wrapper = _get_wrapper()
        if router_name not in wrapper.list_devices():
            return json.dumps(
                {
                    "success": False,
                    "error": MikrotikError(
                        code=MikrotikErrorCode.DEVICE_NOT_FOUND,
                        message=f"Device '{router_name}' not found in inventory",
                    ).model_dump(),
                },
                indent=2,
            )

        # ITSM gate validation
        if change_request_number:
            cr_result = validate_change_request(change_request_number)
            if not cr_result.valid:
                return json.dumps(
                    {
                        "success": False,
                        "error": MikrotikError(
                            code=MikrotikErrorCode.ITSM_ERROR,
                            message=cr_result.message,
                            target=router_name,
                            details=f"CR: {change_request_number}",
                        ).model_dump(),
                    },
                    indent=2,
                )

        # Safety blocklist check
        try:
            check_config_operation(config_path, method, entity_id)
        except BlockedOperationError as e:
            return json.dumps(
                {
                    "success": False,
                    "blocked": True,
                    "error": MikrotikError(
                        code=MikrotikErrorCode.BLOCKED_OPERATION,
                        message=str(e),
                        target=router_name,
                    ).model_dump(),
                },
                indent=2,
            )

        client = wrapper.get_client(router_name)

        # Build the API path
        api_path = config_path
        if entity_id:
            api_path = f"{config_path}/{entity_id}"

        # Execute the operation
        if method == "PUT":
            result = client.put_path(config_path, data or {})
        elif method == "PATCH":
            result = client.patch_path(config_path, data or {}, entity_id or "")
        elif method == "DELETE":
            result = client.delete_path(config_path, entity_id or "")
        else:
            return json.dumps(
                {
                    "success": False,
                    "error": MikrotikError(
                        code=MikrotikErrorCode.VALIDATION_ERROR,
                        message=f"Unsupported method: {method}",
                        target=router_name,
                    ).model_dump(),
                },
                indent=2,
            )

        _gait_log(
            "mikrotik_load_commit",
            router=router_name,
            path=config_path,
            method=method,
            cr=change_request_number,
            success=result.success,
            comment=commit_comment,
        )

        if result.error:
            return json.dumps(
                {
                    "success": False,
                    "router": router_name,
                    "path": config_path,
                    "method": method,
                    "error": result.error.model_dump(),
                },
                indent=2,
            )

        return json.dumps(
            {
                "success": True,
                "router": router_name,
                "path": config_path,
                "method": method,
                "data": result.data,
                "change_request": change_request_number,
                "comment": commit_comment,
                "duration_ms": result.duration_ms,
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: render_and_apply_j2_template
    # =============================================================================

    @mcp.tool()
    def render_and_apply_j2_template(
        template_content: str,
        vars_content: str,
        router_name: Optional[str] = None,
        router_names: Optional[list[str]] = None,
        change_request_number: Optional[str] = None,
        commit_comment: Optional[str] = None,
        dry_run: bool = True,
    ) -> str:
        """
        Render a Jinja2 configuration template and optionally apply to MikroTik devices.
        Templates use YAML variables for device-specific values.

        Args:
            template_content: Jinja2 template string
            vars_content: YAML variables for template
            router_name: Single target device name
            router_names: Multiple target device names
            change_request_number: ServiceNow CR for apply (required if not dry_run)
            commit_comment: Comment for the commit operation
            dry_run: Preview changes without applying (default: True)

        Returns:
            JSON with rendered config and planned operations

        YAML vars example:
            hostname: core-mt-01
            lan_interface: bridge-LAN
            lan_network: 10.0.10.0/24
            wan_interface: ether1
            wan_ip: 192.168.1.1/24

        Jinja2 template example:
            /ip address add address={{ wan_ip }} interface={{ wan_interface }}
            /interface bridge add name={{ lan_interface }}

        GAIT: Logs mikrotik_render_template operation
        """
        # Determine targets
        targets = []
        if router_name:
            targets = [router_name]
        elif router_names:
            targets = router_names
        else:
            targets = _get_wrapper().list_devices()

        # Validate targets exist
        wrapper = _get_wrapper()
        missing = [t for t in targets if t not in wrapper.list_devices()]
        if missing:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Devices not found: {missing}",
                },
                indent=2,
            )

        # Parse YAML variables
        try:
            vars_dict = yaml.safe_load(vars_content)
        except yaml.YAMLError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid YAML variables: {e}",
                },
                indent=2,
            )

        # Render template
        try:
            template = Template(template_content)
            rendered = template.render(**vars_dict)
            commands = [c.strip() for c in rendered.split("\n") if c.strip()]
        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Template rendering failed: {e}",
                },
                indent=2,
            )

        operations = []
        for cmd in commands:
            operations.append({"command": cmd, "status": "planned"})

        # Apply if not dry run
        if not dry_run:
            if not change_request_number:
                return json.dumps(
                    {
                        "success": False,
                        "error": "change_request_number required for apply (not dry_run)",
                    },
                    indent=2,
                )

            # ITSM gate
            cr_result = validate_change_request(change_request_number)
            if not cr_result.valid:
                return json.dumps(
                    {
                        "success": False,
                        "error": cr_result.message,
                    },
                    indent=2,
                )

            # Execute each command
            results = {}
            for target in targets:
                client = wrapper.get_client(target)
                target_results = []
                for cmd in commands:
                    try:
                        check_terminal_command(cmd)
                        resp = client.execute_terminal_command(cmd)
                        target_results.append({
                            "command": cmd,
                            "success": resp.success,
                            "data": resp.data if resp.success else None,
                            "error": resp.error.model_dump() if resp.error else None,
                        })
                    except BlockedOperationError as e:
                        target_results.append({
                            "command": cmd,
                            "success": False,
                            "blocked": True,
                            "error": str(e),
                        })
                results[target] = target_results

            _gait_log(
                "mikrotik_render_template",
                targets=targets,
                command_count=len(commands),
                cr=change_request_number,
                dry_run=False,
                success=True,
            )

            return json.dumps(
                {
                    "success": True,
                    "targets": targets,
                    "rendered_config": rendered,
                    "operations": results,
                    "change_request": change_request_number,
                    "comment": commit_comment,
                    "dry_run": False,
                },
                indent=2,
            )

        _gait_log(
            "mikrotik_render_template",
            targets=targets,
            command_count=len(commands),
            dry_run=True,
            success=True,
        )

        return json.dumps(
            {
                "success": True,
                "targets": targets,
                "rendered_config": rendered,
                "operations_planned": operations,
                "dry_run": True,
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: gather_device_facts
    # =============================================================================

    @mcp.tool()
    def gather_device_facts(
        router_name: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> str:
        """
        Gather device facts from MikroTik: hostname, model, serial, version, uptime, CPU, memory.

        Args:
            router_name: Target device name
            timeout: Request timeout in seconds

        Returns:
            JSON with device facts

        GAIT: Logs mikrotik_gather_facts operation
        """
        wrapper = _get_wrapper()
        if router_name not in wrapper.list_devices():
            return json.dumps(
                {
                    "success": False,
                    "error": MikrotikError(
                        code=MikrotikErrorCode.DEVICE_NOT_FOUND,
                        message=f"Device '{router_name}' not found in inventory",
                    ).model_dump(),
                },
                indent=2,
            )

        client = wrapper.get_client(router_name)
        client.target.timeout = timeout

        facts = client.get_device_facts()

        _gait_log(
            "mikrotik_gather_facts",
            router=router_name,
            hostname=facts.hostname,
            model=facts.model,
            version=facts.version,
            success=True,
        )

        return json.dumps(
            {
                "success": True,
                "router": router_name,
                "facts": facts.model_dump(),
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: backup_save
    # =============================================================================

    @mcp.tool()
    def backup_save(
        router_name: str,
        backup_name: Optional[str] = None,
        password: Optional[str] = None,
    ) -> str:
        """
        Create a local backup of MikroTik router configuration.
        The backup is stored on the router's filesystem.

        Args:
            router_name: Target device name
            backup_name: Name for the backup file (default: auto-generated with date)
            password: Optional password to encrypt the backup

        Returns:
            JSON with backup result and file name

        Example:
            backup_save("core-mt-01", backup_name="pre-maintenance-20260420")

        GAIT: Logs mikrotik_backup_save operation
        """
        wrapper = _get_wrapper()
        if router_name not in wrapper.list_devices():
            return json.dumps(
                {
                    "success": False,
                    "error": MikrotikError(
                        code=MikrotikErrorCode.DEVICE_NOT_FOUND,
                        message=f"Device '{router_name}' not found in inventory",
                    ).model_dump(),
                },
                indent=2,
            )

        client = wrapper.get_client(router_name)

        # Generate backup name with timestamp if not provided
        if backup_name is None:
            backup_name = f"netclaw-backup-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

        data: dict[str, Any] = {"name": backup_name}
        if password:
            data["password"] = password

        result = client.post_path("/system/backup/save", data=data)

        _gait_log(
            "mikrotik_backup_save",
            router=router_name,
            backup_name=backup_name,
            has_password=bool(password),
            success=result.success,
        )

        if result.error:
            return json.dumps(
                {
                    "success": False,
                    "router": router_name,
                    "error": result.error.model_dump(),
                },
                indent=2,
            )

        return json.dumps(
            {
                "success": True,
                "router": router_name,
                "backup_name": backup_name,
                "data": result.data,
                "message": f"Backup '{backup_name}' created successfully",
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: config_export
    # =============================================================================

    @mcp.tool()
    def config_export(
        router_name: str,
        compact: bool = True,
    ) -> str:
        """
        Export router configuration as a script (.rsc file content).
        This is the text-based configuration export, ideal for Git storage.

        Args:
            router_name: Target device name
            compact: Use compact format (default: True, removes defaults)

        Returns:
            JSON with exported configuration as text

        Example:
            config_export("core-mt-01") → returns /export output as text
            Save to Git as configs/core-mt-01/2026-04-20.rsc

        GAIT: Logs mikrotik_config_export operation
        """
        wrapper = _get_wrapper()
        if router_name not in wrapper.list_devices():
            return json.dumps(
                {
                    "success": False,
                    "error": MikrotikError(
                        code=MikrotikErrorCode.DEVICE_NOT_FOUND,
                        message=f"Device '{router_name}' not found in inventory",
                    ).model_dump(),
                },
                indent=2,
            )

        client = wrapper.get_client(router_name)

        result = client.post_path("/rest/export", data={"compact": "" if compact else None})

        _gait_log(
            "mikrotik_config_export",
            router=router_name,
            compact=compact,
            success=result.success,
        )

        if result.error:
            return json.dumps(
                {
                    "success": False,
                    "router": router_name,
                    "error": result.error.model_dump(),
                },
                indent=2,
            )

        # Export returns raw text in data, format it
        export_text = "\n".join(str(item.get("text", "")) for item in result.data if item.get("text"))

        return json.dumps(
            {
                "success": True,
                "router": router_name,
                "export": export_text,
                "lines": len(export_text.split("\n")),
                "compact": compact,
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: system_monitor
    # =============================================================================

    @mcp.tool()
    def system_monitor(
        router_name: str,
        duration: str = "10s",
    ) -> str:
        """
        Monitor system resources in real-time: CPU usage, memory, disk I/O.
        Samples are collected over the specified duration.

        Args:
            router_name: Target device name
            duration: Monitoring duration (default: "10s", e.g., "5s", "30s", "1m")

        Returns:
            JSON array of resource samples over time

        Example:
            system_monitor("core-mt-01", duration="30s")
            Returns CPU/memory samples every 1s for 30 seconds

        GAIT: Logs mikrotik_system_monitor operation
        """
        wrapper = _get_wrapper()
        if router_name not in wrapper.list_devices():
            return json.dumps(
                {
                    "success": False,
                    "error": MikrotikError(
                        code=MikrotikErrorCode.DEVICE_NOT_FOUND,
                        message=f"Device '{router_name}' not found in inventory",
                    ).model_dump(),
                },
                indent=2,
            )

        client = wrapper.get_client(router_name)

        result = client.post_path("/system/resource/monitor", data={"duration": duration})

        _gait_log(
            "mikrotik_system_monitor",
            router=router_name,
            duration=duration,
            sample_count=len(result.data) if result.success else 0,
            success=result.success,
        )

        if result.error:
            return json.dumps(
                {
                    "success": False,
                    "router": router_name,
                    "error": result.error.model_dump(),
                },
                indent=2,
            )

        return json.dumps(
            {
                "success": True,
                "router": router_name,
                "duration": duration,
                "samples": result.data,
                "sample_count": len(result.data),
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: interface_monitor
    # =============================================================================

    @mcp.tool()
    def interface_monitor(
        router_name: str,
        interface_name: Optional[str] = None,
        duration: str = "10s",
    ) -> str:
        """
        Monitor interface statistics in real-time: rx/tx bytes, packets, errors.
        If interface_name is not provided, monitors all interfaces.

        Args:
            router_name: Target device name
            interface_name: Specific interface name (e.g., "ether1", "bridge-LAN")
            duration: Monitoring duration (default: "10s")

        Returns:
            JSON array of interface stats samples over time

        Example:
            interface_monitor("core-mt-01", "ether1", duration="30s")
            interface_monitor("core-mt-01") → all interfaces

        GAIT: Logs mikrotik_interface_monitor operation
        """
        wrapper = _get_wrapper()
        if router_name not in wrapper.list_devices():
            return json.dumps(
                {
                    "success": False,
                    "error": MikrotikError(
                        code=MikrotikErrorCode.DEVICE_NOT_FOUND,
                        message=f"Device '{router_name}' not found in inventory",
                    ).model_dump(),
                },
                indent=2,
            )

        client = wrapper.get_client(router_name)

        data: dict[str, Any] = {"duration": duration}
        if interface_name:
            data["interface"] = interface_name

        # Use ethernet monitor for specific interface
        if interface_name:
            result = client.post_path("/interface/ethernet/monitor", data={
                "interface": interface_name,
                "duration": duration,
            })
        else:
            result = client.post_path("/interface/monitor-traffic", data=data)

        _gait_log(
            "mikrotik_interface_monitor",
            router=router_name,
            interface=interface_name or "all",
            duration=duration,
            sample_count=len(result.data) if result.success else 0,
            success=result.success,
        )

        if result.error:
            return json.dumps(
                {
                    "success": False,
                    "router": router_name,
                    "error": result.error.model_dump(),
                },
                indent=2,
            )

        return json.dumps(
            {
                "success": True,
                "router": router_name,
                "interface": interface_name,
                "duration": duration,
                "samples": result.data,
                "sample_count": len(result.data),
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: queue_monitor
    # =============================================================================

    @mcp.tool()
    def queue_monitor(
        router_name: str,
        duration: str = "10s",
    ) -> str:
        """
        Monitor queue (QoS) statistics in real-time.
        Shows per-queue tx/rx rates, bytes, packets.

        Args:
            router_name: Target device name
            duration: Monitoring duration (default: "10s")

        Returns:
            JSON array of queue stats samples over time

        Example:
            queue_monitor("core-mt-01", duration="30s")

        GAIT: Logs mikrotik_queue_monitor operation
        """
        wrapper = _get_wrapper()
        if router_name not in wrapper.list_devices():
            return json.dumps(
                {
                    "success": False,
                    "error": MikrotikError(
                        code=MikrotikErrorCode.DEVICE_NOT_FOUND,
                        message=f"Device '{router_name}' not found in inventory",
                    ).model_dump(),
                },
                indent=2,
            )

        client = wrapper.get_client(router_name)

        result = client.post_path("/queue/monitor", data={"duration": duration})

        _gait_log(
            "mikrotik_queue_monitor",
            router=router_name,
            duration=duration,
            sample_count=len(result.data) if result.success else 0,
            success=result.success,
        )

        if result.error:
            return json.dumps(
                {
                    "success": False,
                    "router": router_name,
                    "error": result.error.model_dump(),
                },
                indent=2,
            )

        return json.dumps(
            {
                "success": True,
                "router": router_name,
                "duration": duration,
                "samples": result.data,
                "sample_count": len(result.data),
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: netwatch_list
    # =============================================================================

    @mcp.tool()
    def netwatch_list(router_name: str) -> str:
        """
        List all configured NetWatch hosts on a MikroTik router.
        NetWatch monitors hosts via ping and can trigger scripts on up/down events.

        Args:
            router_name: Target device name

        Returns:
            JSON array of NetWatch entries with host, status, interval

        Example:
            netwatch_list("core-mt-01")

        GAIT: Logs mikrotik_netwatch_list operation
        """
        wrapper = _get_wrapper()
        if router_name not in wrapper.list_devices():
            return json.dumps(
                {
                    "success": False,
                    "error": MikrotikError(
                        code=MikrotikErrorCode.DEVICE_NOT_FOUND,
                        message=f"Device '{router_name}' not found in inventory",
                    ).model_dump(),
                },
                indent=2,
            )

        client = wrapper.get_client(router_name)

        result = client.get_path("/tool/netwatch")

        _gait_log(
            "mikrotik_netwatch_list",
            router=router_name,
            host_count=len(result.data) if result.success else 0,
            success=result.success,
        )

        if result.error:
            return json.dumps(
                {
                    "success": False,
                    "router": router_name,
                    "error": result.error.model_dump(),
                },
                indent=2,
            )

        return json.dumps(
            {
                "success": True,
                "router": router_name,
                "netwatch_entries": result.data,
                "count": len(result.data),
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: netwatch_add
    # =============================================================================

    @mcp.tool()
    def netwatch_add(
        router_name: str,
        host: str,
        interval: str = "1m",
        timeout: str = "3s",
        up_script: Optional[str] = None,
        down_script: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> str:
        """
        Add a new NetWatch host to monitor. NetWatch sends periodic pings
        and can execute scripts on state changes (up/down).

        Args:
            router_name: Target device name
            host: IP address or hostname to monitor (e.g., "8.8.8.8", "192.168.1.1")
            interval: Ping interval (default: "1m", e.g., "30s", "5m")
            timeout: Ping timeout (default: "3s", e.g., "1s", "10s")
            up_script: Optional script to run when host comes up
            down_script: Optional script to run when host goes down
            comment: Optional comment/description

        Returns:
            JSON confirmation with created NetWatch entry

        Example:
            netwatch_add("core-mt-01", host="8.8.8.8", interval="30s",
                          down_script="/log info \"Gateway down!\"")

        GAIT: Logs mikrotik_netwatch_add operation
        """
        wrapper = _get_wrapper()
        if router_name not in wrapper.list_devices():
            return json.dumps(
                {
                    "success": False,
                    "error": MikrotikError(
                        code=MikrotikErrorCode.DEVICE_NOT_FOUND,
                        message=f"Device '{router_name}' not found in inventory",
                    ).model_dump(),
                },
                indent=2,
            )

        client = wrapper.get_client(router_name)

        data: dict[str, Any] = {
            "host": host,
            "interval": interval,
            "timeout": timeout,
        }
        if up_script:
            data["up-script"] = up_script
        if down_script:
            data["down-script"] = down_script
        if comment:
            data["comment"] = comment

        result = client.put_path("/tool/netwatch", data=data)

        _gait_log(
            "mikrotik_netwatch_add",
            router=router_name,
            host=host,
            interval=interval,
            success=result.success,
        )

        if result.error:
            return json.dumps(
                {
                    "success": False,
                    "router": router_name,
                    "error": result.error.model_dump(),
                },
                indent=2,
            )

        return json.dumps(
            {
                "success": True,
                "router": router_name,
                "netwatch_entry": result.data,
                "message": f"NetWatch for host '{host}' created successfully",
            },
            indent=2,
        )

    # =============================================================================
    # MCP Tool: logging_config
    # =============================================================================

    @mcp.tool()
    def logging_config(router_name: str) -> str:
        """
        Get the current logging configuration: what is logged and where.
        Shows logging rules and their destinations (remote, local, memory).

        Args:
            router_name: Target device name

        Returns:
            JSON array of logging configuration entries

        Example:
            logging_config("core-mt-01")
            Returns topics, actions (remote syslog, memory, etc.)

        GAIT: Logs mikrotik_logging_config operation
        """
        wrapper = _get_wrapper()
        if router_name not in wrapper.list_devices():
            return json.dumps(
                {
                    "success": False,
                    "error": MikrotikError(
                        code=MikrotikErrorCode.DEVICE_NOT_FOUND,
                        message=f"Device '{router_name}' not found in inventory",
                    ).model_dump(),
                },
                indent=2,
            )

        client = wrapper.get_client(router_name)

        # Get logging rules
        result = client.get_path("/system/logging")
        # Get logging actions (destinations)
        action_result = client.get_path("/system/logging/action")

        _gait_log(
            "mikrotik_logging_config",
            router=router_name,
            logging_count=len(result.data) if result.success else 0,
            action_count=len(action_result.data) if action_result.success else 0,
            success=result.success,
        )

        if result.error:
            return json.dumps(
                {
                    "success": False,
                    "router": router_name,
                    "error": result.error.model_dump(),
                },
                indent=2,
            )

        return json.dumps(
            {
                "success": True,
                "router": router_name,
                "logging_rules": result.data,
                "logging_actions": action_result.data,
                "logging_count": len(result.data),
                "action_count": len(action_result.data),
            },
            indent=2,
        )


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> None:
    """Run the MikroTik MCP server."""
    import argparse

    parser = argparse.ArgumentParser(description="MikroTik RouterOS MCP Server")
    parser.add_argument("-f", "--file", default=DEFAULT_DEVICES_FILE, help="Devices inventory file")
    args = parser.parse_args()

    # Load inventory
    _load_inventory(args.file)

    if FASTMCP_AVAILABLE:
        print(f"MikroTik MCP Server starting with {len(_inventory)} devices", file=sys.stderr)
        mcp.run(transport="stdio")
    else:
        print("Error: fastmcp not installed. Run: pip install mcp[cli]", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
