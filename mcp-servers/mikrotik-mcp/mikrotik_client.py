"""
MikroTik MCP Server - REST API Client
RouterOS REST API v7 (tested against v7.22.1)
Supports HTTP/HTTPS on port 8728/8729 with Basic Auth
"""

from __future__ import annotations

import json
import time
import urllib.parse
from typing import Any, Optional
from urllib3.exceptions import InsecureRequestWarning

import requests
from requests.auth import HTTPBasicAuth

# Suppress only the single InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from .models import (
    MikrotikApiResponse,
    MikrotikDeviceFacts,
    MikrotikError,
    MikrotikErrorCode,
    MikrotikTarget,
)


class MikrotikApiError(Exception):
    """Raised when a MikroTik API call fails."""

    def __init__(self, code: MikrotikErrorCode, message: str, target: Optional[str] = None, details: Optional[str] = None):
        self.code = code
        self.message = message
        self.target = target
        self.details = details
        super().__init__(message)


class MikrotikClient:
    """HTTP client for MikroTik RouterOS REST API."""

    # Base paths
    PATH_SYSTEM_RESOURCE = "/rest/system/resource"
    PATH_SYSTEM_IDENTITY = "/rest/system/identity"
    PATH_SYSTEM_HISTORY = "/rest/system/history"
    PATH_TERMINAL = "/rest/terminal/sync"
    PATH_EXPORT = "/rest/export"

    # All supported REST API categories (from OpenAPI spec v7.22.1)
    SUPPORTED_PATHS = {
        # IP
        "/ip/address", "/ip/arp", "/ip/cloud", "/ip/dhcp-client", "/ip/dhcp-relay",
        "/ip/dhcp-server", "/ip/dns", "/ip/firewall", "/ip/hotspot", "/ip/ipsec",
        "/ip/kid-control", "/ip/media", "/ip/nat-pmp", "/ip/neighbor", "/ip/packing",
        "/ip/pool", "/ip/proxy", "/ip/reverse-proxy", "/ip/route", "/ip/service",
        "/ip/settings", "/ip/smb", "/ip/socks", "/ip/socksify", "/ip/ssh", "/ip/tftp",
        "/ip/traffic-flow", "/ip/upnp", "/ip/vrf",
        # IPv6
        "/ipv6/address", "/ipv6/dhcp-client", "/ipv6/dhcp-relay", "/ipv6/dhcp-server",
        "/ipv6/dns", "/ipv6/firewall", "/ipv6/mroute", "/ipv6/nd", "/ipv6/route",
        "/ipv6/settings",
        # Routing
        "/routing/bgp", "/routing/ospf", "/routing/rip", "/routing/isis", "/routing/pimsm",
        "/routing/bfd", "/routing/igmp-proxy", "/routing/gmp", "/routing/rpki",
        "/routing/filter", "/routing/rule", "/routing/route", "/routing/table",
        "/routing/stats", "/routing/settings", "/routing/id",
        # Interface
        "/interface", "/interface/ethernet", "/interface/bridge", "/interface/vlan",
        "/interface/bonding", "/interface/vrrp", "/interface/vxlan", "/interface/gre",
        "/interface/gre6", "/interface/ovpn-client", "/interface/ovpn-server",
        "/interface/l2tp-client", "/interface/l2tp-server", "/interface/pppoe-client",
        "/interface/pppoe-server", "/interface/pptp-client", "/interface/pptp-server",
        "/interface/sstp-client", "/interface/sstp-server", "/interface/wireguard",
        "/interface/wifi", "/interface/lte", "/interface/macsec", "/interface/macvlan",
        "/interface/mesh", "/interface/eoip", "/interface/ipip", "/interface/ipipv6",
        # PPP
        "/ppp", "/ppp/secret", "/ppp/profile", "/ppp/active", "/ppp/aaa", "/ppp/l2tp-secret",
        # User
        "/user", "/user/active", "/user/group", "/user/ssh-keys",
        # System
        "/system/resource", "/system/identity", "/system/history", "/system/backup",
        "/system/script", "/system/scheduler", "/system/package", "/system/log",
        "/system/clock", "/system/health", "/system/leds", "/system/license",
        "/system/logging", "/system/ntp", "/system/reboot", "/system/shutdown",
        # Certificate
        "/certificate", "/certificate/crl", "/certificate/scep-server",
        # Tool
        "/tool/ping", "/tool/traceroute", "/tool/bandwidth-test", "/tool/sniffer",
        "/tool/netwatch", "/tool/fetch", "/tool/mac-scan", "/tool/ip-scan",
        # Queue
        "/queue/interface", "/queue/simple", "/queue/tree", "/queue/type",
        # SNMP
        "/snmp",
        # RADIUS
        "/radius",
        # Log
        "/log",
        # Terminal
        "/terminal/sync",
    }

    def __init__(self, target: MikrotikTarget):
        self.target = target
        self.base_url = f"{'https' if target.use_https else 'http'}://{target.host}:{target.port}"
        self.auth = HTTPBasicAuth(target.username, target.password)
        self.verify_tls = not target.tls_skip_verify
        self.timeout = target.timeout

    def _classify_error(self, exc: Exception) -> MikrotikErrorCode:
        """Map exception to MikrotikErrorCode."""
        msg = str(exc).lower()
        if "timeout" in msg or "timed out" in msg:
            return MikrotikErrorCode.TIMEOUT_ERROR
        elif "certificate" in msg or "ssl" in msg or "tls" in msg:
            return MikrotikErrorCode.TLS_ERROR
        elif "auth" in msg or "unauthorized" in msg or "401" in msg or "403" in msg:
            return MikrotikErrorCode.AUTH_ERROR
        elif "connection" in msg or "refused" in msg:
            return MikrotikErrorCode.CONNECTION_ERROR
        else:
            return MikrotikErrorCode.API_ERROR

    def _sanitize_error_message(self, message: str) -> str:
        """Remove sensitive info from error messages."""
        # Remove potential credential leaks
        sensitive_patterns = [
            (r'password["\']?\s*[:=]\s*["\'].*?["\']', 'password=***'),
            (r'Bearer\s+[^\s]+', 'Bearer ***'),
            (r'token["\']?\s*[:=]\s*["\'].*?["\']', 'token=***'),
        ]
        for pattern, replacement in sensitive_patterns:
            import re
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        return message

    def _build_url(self, path: str, params: Optional[dict[str, str]] = None) -> str:
        """Build full URL with optional query parameters."""
        url = f"{self.base_url}{path}"
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"
        return url

    def _parse_api_error(self, response: requests.Response) -> Optional[MikrotikError]:
        """Parse MikroTik API error response."""
        try:
            error_data = response.json()
            if "error" in error_data:
                return MikrotikError(
                    code=MikrotikErrorCode.API_ERROR,
                    message=error_data.get("message", "Unknown API error"),
                    target=self.target.name,
                    details=error_data.get("detail", ""),
                )
        except (json.JSONDecodeError, ValueError):
            pass

        # HTTP status-based errors
        if response.status_code == 400:
            return MikrotikError(
                code=MikrotikErrorCode.API_ERROR,
                message=f"Bad request: {response.text[:200]}",
                target=self.target.name,
            )
        elif response.status_code == 401:
            return MikrotikError(
                code=MikrotikErrorCode.AUTH_ERROR,
                message="Authentication failed — check username/password",
                target=self.target.name,
            )
        elif response.status_code == 403:
            return MikrotikError(
                code=MikrotikErrorCode.AUTH_ERROR,
                message="Access forbidden — insufficient permissions",
                target=self.target.name,
            )
        elif response.status_code == 404:
            return MikrotikError(
                code=MikrotikErrorCode.PATH_ERROR,
                message=f"Path not found: {response.url}",
                target=self.target.name,
            )
        elif response.status_code >= 500:
            return MikrotikError(
                code=MikrotikErrorCode.CONNECTION_ERROR,
                message="RouterOS server error",
                target=self.target.name,
            )
        return None

    def request(
        self,
        path: str,
        method: str = "GET",
        data: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, str]] = None,
    ) -> MikrotikApiResponse:
        """Make an HTTP request to the MikroTik REST API."""
        start_time = time.time()
        url = self._build_url(path, params)
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        try:
            if method == "GET":
                resp = requests.get(
                    url,
                    auth=self.auth,
                    headers=headers,
                    verify=self.verify_tls,
                    timeout=self.timeout,
                )
            elif method == "POST":
                resp = requests.post(
                    url,
                    auth=self.auth,
                    headers=headers,
                    json=data,
                    verify=self.verify_tls,
                    timeout=self.timeout,
                )
            elif method == "PUT":
                resp = requests.put(
                    url,
                    auth=self.auth,
                    headers=headers,
                    json=data,
                    verify=self.verify_tls,
                    timeout=self.timeout,
                )
            elif method == "PATCH":
                resp = requests.patch(
                    url,
                    auth=self.auth,
                    headers=headers,
                    json=data,
                    verify=self.verify_tls,
                    timeout=self.timeout,
                )
            elif method == "DELETE":
                resp = requests.delete(
                    url,
                    auth=self.auth,
                    headers=headers,
                    verify=self.verify_tls,
                    timeout=self.timeout,
                )
            else:
                return MikrotikApiResponse(
                    target=self.target.name,
                    path=path,
                    method=method,
                    status_code=0,
                    success=False,
                    error=MikrotikError(
                        code=MikrotikErrorCode.VALIDATION_ERROR,
                        message=f"Unsupported HTTP method: {method}",
                        target=self.target.name,
                    ),
                )

            duration_ms = int((time.time() - start_time) * 1000)

            # Check for API-level errors (MikroTik returns 200 with error JSON)
            api_error = self._parse_api_error(resp)
            if api_error:
                return MikrotikApiResponse(
                    target=self.target.name,
                    path=path,
                    method=method,
                    status_code=resp.status_code,
                    success=False,
                    error=api_error,
                    duration_ms=duration_ms,
                )

            # Parse successful response
            try:
                response_data = resp.json()
                if not isinstance(response_data, list):
                    response_data = [response_data]
            except (json.JSONDecodeError, ValueError):
                response_data = [{"raw": resp.text}]

            return MikrotikApiResponse(
                target=self.target.name,
                path=path,
                method=method,
                status_code=resp.status_code,
                data=response_data,
                success=True,
                duration_ms=duration_ms,
            )

        except requests.exceptions.Timeout as e:
            return MikrotikApiResponse(
                target=self.target.name,
                path=path,
                method=method,
                status_code=0,
                success=False,
                error=MikrotikError(
                    code=MikrotikErrorCode.TIMEOUT_ERROR,
                    message=f"Request timeout after {self.timeout}s",
                    target=self.target.name,
                    details=str(e),
                ),
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except requests.exceptions.ConnectionError as e:
            return MikrotikApiResponse(
                target=self.target.name,
                path=path,
                method=method,
                status_code=0,
                success=False,
                error=MikrotikError(
                    code=MikrotikErrorCode.CONNECTION_ERROR,
                    message=f"Connection failed to {self.target.host}:{self.target.port}",
                    target=self.target.name,
                    details=str(e),
                ),
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except requests.exceptions.SSLError as e:
            return MikrotikApiResponse(
                target=self.target.name,
                path=path,
                method=method,
                status_code=0,
                success=False,
                error=MikrotikError(
                    code=MikrotikErrorCode.TLS_ERROR,
                    message="TLS/SSL error — enable tls_skip_verify for self-signed certs",
                    target=self.target.name,
                    details=str(e),
                ),
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            return MikrotikApiResponse(
                target=self.target.name,
                path=path,
                method=method,
                status_code=0,
                success=False,
                error=MikrotikError(
                    code=self._classify_error(e),
                    message=self._sanitize_error_message(str(e)),
                    target=self.target.name,
                ),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    def get_path(self, path: str, params: Optional[dict[str, str]] = None) -> MikrotikApiResponse:
        """GET request shorthand."""
        return self.request(path, "GET", params=params)

    def post_path(self, path: str, data: Optional[dict[str, Any]] = None) -> MikrotikApiResponse:
        """POST request shorthand."""
        return self.request(path, "POST", data=data)

    def put_path(self, path: str, data: dict[str, Any]) -> MikrotikApiResponse:
        """PUT request shorthand."""
        return self.request(path, "PUT", data=data)

    def patch_path(self, path: str, data: dict[str, Any], entity_id: str) -> MikrotikApiResponse:
        """PATCH request shorthand (uses /path/{id} format)."""
        return self.request(f"{path}/{entity_id}", "PATCH", data=data)

    def delete_path(self, path: str, entity_id: str) -> MikrotikApiResponse:
        """DELETE request shorthand (uses /path/{id} format)."""
        return self.request(f"{path}/{entity_id}", "DELETE")

    def execute_terminal_command(self, command: str) -> MikrotikApiResponse:
        """Execute a CLI command via /rest/terminal/sync."""
        return self.post_path(
            self.PATH_TERMINAL,
            data={"command": command},
        )

    def get_device_facts(self) -> MikrotikDeviceFacts:
        """Gather device facts from /system/resource and /system/identity."""
        resource_resp = self.get_path(self.PATH_SYSTEM_RESOURCE)
        identity_resp = self.get_path(self.PATH_SYSTEM_IDENTITY)

        resource_data = resource_resp.data if resource_resp.success else []
        identity_data = identity_resp.data if identity_resp.success else []

        return MikrotikDeviceFacts.from_api_response(
            target=self.target.name,
            resource_data=resource_data,
            identity_data=identity_data,
        )

    def get_config_export(self) -> MikrotikApiResponse:
        """Get configuration export via /rest/export."""
        return self.post_path(self.PATH_EXPORT, data={})

    def get_config_history(self) -> MikrotikApiResponse:
        """Get configuration history via /rest/system/history."""
        return self.get_path(self.PATH_SYSTEM_HISTORY)


class MikrotikClientWrapper:
    """Wrapper managing multiple MikroTik device clients."""

    def __init__(self, targets: dict[str, MikrotikTarget]):
        self._targets = targets
        self._clients: dict[str, MikrotikClient] = {}

    def get_client(self, name: str) -> MikrotikClient:
        """Get or create a client for the named device."""
        if name not in self._clients:
            target = self._targets.get(name)
            if not target:
                raise MikrotikApiError(
                    code=MikrotikErrorCode.DEVICE_NOT_FOUND,
                    message=f"Device '{name}' not found in inventory",
                )
            self._clients[name] = MikrotikClient(target)
        return self._clients[name]

    def list_devices(self) -> list[str]:
        """List all configured device names."""
        return sorted(self._targets.keys())

    def get_target(self, name: str) -> Optional[MikrotikTarget]:
        """Get target config by name."""
        return self._targets.get(name)

    def reload_from_dict(self, targets_dict: dict[str, dict]) -> None:
        """Reload device inventory from a dictionary."""
        self._targets = {}
        self._clients = {}
        for name, cfg in targets_dict.items():
            self._targets[name] = MikrotikTarget(name=name, **cfg)
