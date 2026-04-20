"""
MikroTik MCP Server - Safety Blocklists
Prevents destructive operations via REST API
Follows the same pattern as JunOS skill block.cmd/block.cfg
"""

from __future__ import annotations

import re
from typing import Optional

# =============================================================================
# Command Blocklist (CLI via /rest/terminal/sync)
# Matches patterns that would cause disruption
# =============================================================================

BLOCK_COMMANDS = [
    # Reboot/Shutdown
    re.compile(r"^\s*/system/reboot", re.IGNORECASE),
    re.compile(r"^\s*/system/shutdown", re.IGNORECASE),
    re.compile(r"^\s*/system/reset-configuration", re.IGNORECASE),
    # Certificate operations (may break TLS)
    re.compile(r"^\s*/certificate/.*remove", re.IGNORECASE),
    re.compile(r"^\s*/certificate/.*reset", re.IGNORECASE),
    re.compile(r"^\s*/certificate/.*uninstall", re.IGNORECASE),
    # File operations (dangerous)
    re.compile(r"^\s*/file/remove", re.IGNORECASE),
    re.compile(r"^\s*/file/export", re.IGNORECASE),
    # User operations (may lock out admins)
    re.compile(r"^\s*/user/.*remove", re.IGNORECASE),
    re.compile(r"^\s*/user/.*disable", re.IGNORECASE),
    # Package operations (RouterOS packages)
    re.compile(r"^\s*/system/package/.*disable", re.IGNORECASE),
    re.compile(r"^\s*/system/package/.*remove", re.IGNORECASE),
    re.compile(r"^\s*/system/package/.*uninstall", re.IGNORECASE),
    # License operations
    re.compile(r"^\s*/system/license/.*remove", re.IGNORECASE),
    re.compile(r"^\s*/system/license/.*reset", re.IGNORECASE),
    # Reset operations
    re.compile(r"^\s*/interface/.*reset", re.IGNORECASE),
    re.compile(r"^\s*/ip/.*reset", re.IGNORECASE),
    # Dangerous system commands
    re.compile(r"^\s*/system/backup/.*remove", re.IGNORECASE),
    re.compile(r"^\s*/quit", re.IGNORECASE),
    re.compile(r"^\s*quit", re.IGNORECASE),
    re.compile(r"^\s*/exit", re.IGNORECASE),
    re.compile(r"^\s*exit", re.IGNORECASE),
]

# =============================================================================
# Config Blocklist (Direct REST API config changes)
# Patterns that match dangerous PATCH/PUT/DELETE operations
# =============================================================================

BLOCK_CONFIG_PATHS = [
    # Certificate removal/blocking
    "/certificate/",  # Certificate management
    # User removal/disabling
    re.compile(r"^/user/[^/]+$"),  # Direct user entity (not sub-paths)
    # Interface disabling
    re.compile(r"^/interface/.*/disable$"),
    # System dangerous operations
    "/system/reset-configuration",
    "/system/reboot",
    "/system/shutdown",
    # Package operations
    re.compile(r"^/system/package/.*"),
    # License
    "/system/license/",
    # Backup removal
    re.compile(r"^/system/backup/.*remove$"),
]

# =============================================================================
# Blocklist checking functions
# =============================================================================


def is_command_blocked(command: str) -> tuple[bool, Optional[str]]:
    """
    Check if a terminal command is blocklisted.

    Args:
        command: CLI command string to check

    Returns:
        (blocked: bool, reason: Optional[str])
        If blocked, reason explains why
    """
    for pattern in BLOCK_COMMANDS:
        if pattern.search(command):
            return True, f"Command matches blocklist pattern: {pattern.pattern}"
    return False, None


def is_config_blocked(path: str, method: str = "PATCH") -> tuple[bool, Optional[str]]:
    """
    Check if a REST API config operation is blocklisted.

    Args:
        path: REST API path (e.g., /user/admin)
        method: HTTP method (PUT, PATCH, DELETE)

    Returns:
        (blocked: bool, reason: Optional[str])
    """
    # Some paths are always blocked regardless of method
    always_blocked = [
        "/system/reset-configuration",
        "/system/reboot",
        "/system/shutdown",
        "/certificate/remove",
    ]
    for blocked in always_blocked:
        if path == blocked or path.startswith(blocked + "/"):
            return True, f"Path is always blocklisted: {blocked}"

    for pattern in BLOCK_CONFIG_PATHS:
        if isinstance(pattern, re.Pattern):
            if pattern.search(path):
                return True, f"Path matches blocklist pattern: {pattern.pattern}"
        elif path == pattern or path.startswith(pattern):
            return True, f"Path is blocklisted: {pattern}"

    return False, None


def check_terminal_command(command: str) -> None:
    """
    Raise BlockedOperationError if command is blocklisted.

    Args:
        command: CLI command to check

    Raises:
        BlockedOperationError: If command is blocklisted
    """
    blocked, reason = is_command_blocked(command)
    if blocked:
        raise BlockedOperationError(f"Blocked command: {reason}")


def check_config_operation(path: str, method: str, entity_id: Optional[str] = None) -> None:
    """
    Raise BlockedOperationError if config operation is blocklisted.

    Args:
        path: REST API path
        method: HTTP method
        entity_id: Optional entity ID

    Raises:
        BlockedOperationError: If operation is blocklisted
    """
    blocked, reason = is_config_blocked(path, method)
    if blocked:
        raise BlockedOperationError(f"Blocked config operation: {reason}")


class BlockedOperationError(Exception):
    """Raised when an operation is blocked by safety rules."""

    pass
