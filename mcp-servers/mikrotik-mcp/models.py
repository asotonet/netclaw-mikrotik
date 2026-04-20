"""
MikroTik MCP Server - Pydantic Data Models
RouterOS REST API v7 (tested against v7.22.1)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Error Taxonomy
# =============================================================================


class MikrotikErrorCode(str, Enum):
    """Structured error codes for MikroTik API errors."""

    CONNECTION_ERROR = "CONNECTION_ERROR"
    TLS_ERROR = "TLS_ERROR"
    AUTH_ERROR = "AUTH_ERROR"
    PATH_ERROR = "PATH_ERROR"
    API_ERROR = "API_ERROR"
    ITSM_ERROR = "ITSM_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    DEVICE_NOT_FOUND = "DEVICE_NOT_FOUND"
    BLOCKED_OPERATION = "BLOCKED_OPERATION"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class MikrotikError(BaseModel):
    """Structured error envelope — credentials never appear in messages."""

    code: MikrotikErrorCode
    message: str
    target: Optional[str] = None
    details: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# =============================================================================
# Device Target Model
# =============================================================================


class MikrotikTarget(BaseModel):
    """Device configuration for a single MikroTik router."""

    name: str = Field(..., min_length=1, max_length=64)
    host: str = Field(..., description="IP address or hostname")
    port: int = Field(default=8728, ge=1, le=65535, description="REST API port (8728=HTTP, 8729=HTTPS)")
    username: str = Field(default="admin")
    password: str = Field(default="")
    use_https: bool = Field(default=False, description="Use HTTPS (port 8729)")
    tls_skip_verify: bool = Field(default=False, description="Skip TLS cert verification (for self-signed)")
    timeout: int = Field(default=60, ge=1, le=300, description="Request timeout in seconds")
    version: Optional[str] = Field(default=None, description="RouterOS version override")

    @field_validator("host")
    @classmethod
    def host_must_not_contain_credentials(cls, v: str) -> str:
        # Prevent credential leakage in host field
        if "@" in v:
            raise ValueError("Credentials must not be embedded in host")
        return v


class MikrotikDeviceInventory(BaseModel):
    """Device inventory containing all MikroTik targets."""

    devices: dict[str, MikrotikTarget] = Field(default_factory=dict)

    def add_device(self, target: MikrotikTarget) -> None:
        self.devices[target.name] = target

    def get_device(self, name: str) -> Optional[MikrotikTarget]:
        return self.devices.get(name)

    def list_devices(self) -> list[str]:
        return sorted(self.devices.keys())


# =============================================================================
# API Request/Response Models
# =============================================================================


class MikrotikApiRequest(BaseModel):
    """Base request model for MikroTik API calls."""

    target: str
    path: str = Field(..., description="REST API path (e.g., /ip/address)")
    method: str = Field(default="GET", pattern="^(GET|POST|PUT|PATCH|DELETE)$")
    data: Optional[dict[str, Any]] = Field(default=None, description="JSON body for POST/PUT/PATCH")
    params: Optional[dict[str, str]] = Field(default=None, description="Query parameters")


class MikrotikApiResponse(BaseModel):
    """Structured API response envelope."""

    target: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    path: str
    method: str
    status_code: int
    data: list[dict[str, str]] = Field(default_factory=list)
    success: bool
    error: Optional[MikrotikError] = None
    duration_ms: Optional[int] = None


# =============================================================================
# Config Diff Models
# =============================================================================


class MikrotikConfigDiff(BaseModel):
    """Configuration diff result comparing current vs historical state."""

    target: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    path: str
    current: list[dict[str, str]] = Field(default_factory=list)
    history: list[dict[str, str]] = Field(default_factory=list)
    added: list[dict[str, str]] = Field(default_factory=list)
    removed: list[dict[str, str]] = Field(default_factory=list)
    modified: list[dict[str, str]] = Field(default_factory=list)


# =============================================================================
# Device Facts Model
# =============================================================================


class MikrotikDeviceFacts(BaseModel):
    """Device information gathered from /system/resource and /system/identity."""

    target: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hostname: str = ""
    model: str = ""
    serial_number: str = ""
    version: str = ""
    board_name: str = ""
    uptime: str = ""
    cpu_load: str = ""
    memory_used: str = ""
    memory_total: str = ""
    disk_used: str = ""
    disk_total: str = ""
    architecture_name: str = ""
    platform: str = ""

    @classmethod
    def from_api_response(cls, target: str, resource_data: list[dict], identity_data: list[dict]) -> "MikrotikDeviceFacts":
        """Construct facts from API response data."""
        facts = cls(target=target)
        if resource_data:
            r = resource_data[0] if resource_data else {}
            facts.model = r.get("model", "")
            facts.serial_number = r.get("serial-number", "")
            facts.version = r.get("version", "")
            facts.board_name = r.get("board-name", "")
            facts.uptime = r.get("uptime", "")
            facts.cpu_load = r.get("cpu-load", "")
            facts.memory_used = r.get("memory-used", "")
            facts.memory_total = r.get("memory-total", "")
            facts.disk_used = r.get("disk-used", "")
            facts.disk_total = r.get("disk-total", "")
            facts.architecture_name = r.get("architecture-name", "")
            facts.platform = r.get("platform", "RouterOS")
        if identity_data:
            i = identity_data[0] if identity_data else {}
            facts.hostname = i.get("name", "")
        return facts


# =============================================================================
# Template Models
# =============================================================================


class TemplateRenderRequest(BaseModel):
    """Request to render a Jinja2 config template."""

    template_content: str = Field(..., description="Jinja2 template content")
    vars_content: str = Field(..., description="YAML variables for template")
    target: Optional[str] = Field(default=None, description="Single target router name")
    targets: Optional[list[str]] = Field(default=None, description="Multiple target router names")
    dry_run: bool = Field(default=True, description="Preview without applying")
    commit_comment: Optional[str] = Field(default=None, description="Commit comment / CR reference")


class TemplateRenderResult(BaseModel):
    """Result of template rendering operation."""

    rendered_config: str = ""
    targets: list[str] = Field(default_factory=list)
    dry_run: bool = True
    operations_planned: list[str] = Field(default_factory=list)
    success: bool = True
    error: Optional[str] = None


# =============================================================================
# Config Operations
# =============================================================================


class ConfigOperation(BaseModel):
    """A single configuration operation (create/update/delete)."""

    path: str
    method: str = Field(pattern="^(PUT|PATCH|DELETE)$")
    entity_id: Optional[str] = Field(default=None, description="Entity ID for PATCH/DELETE")
    data: Optional[dict[str, Any]] = Field(default=None, description="Data for PUT/PATCH")
    description: str = ""


class ConfigChangeRequest(BaseModel):
    """A configuration change request with multiple operations."""

    target: str
    operations: list[ConfigOperation] = Field(default_factory=list)
    change_request_number: Optional[str] = Field(default=None, pattern=r"^CHG\d+$")
    dry_run: bool = Field(default=False)
    commit: bool = Field(default=True)


# =============================================================================
# ITSM Models
# =============================================================================


class ItsmsGateResult(BaseModel):
    """Result of ServiceNow CR validation."""

    valid: bool
    cr_number: str
    state: str = ""
    message: str = ""
    bypassed: bool = Field(default=False, description="True when NETCLAW_LAB_MODE=true")


# =============================================================================
# Telemetry Models (for long-polling monitoring)
# =============================================================================


class TelemetrySubscription(BaseModel):
    """Subscription for periodic device monitoring."""

    id: str = Field(default_factory=lambda: f"sub_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")
    target: str
    paths: list[str] = Field(default_factory=list)
    interval_seconds: int = Field(default=10, ge=1, le=3600)
    last_update: Optional[str] = None
    data: list[dict[str, Any]] = Field(default_factory=list)
    active: bool = Field(default=True)
