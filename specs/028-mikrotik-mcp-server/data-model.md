# Data Model: MikroTik MCP Server

**Feature**: 028-mikrotik-mcp-server | **Date**: 2026-04-20

## Entity Relationship

```
MikrotikDeviceInventory
    │
    └─── MikrotikTarget (name, host, port, username, password, use_https, tls_skip_verify, timeout)
            │
            └─── MikrotikClient (HTTP client per device)
                    │
                    └─── MikrotikApiResponse (target, path, method, status_code, data, success, error)
                            │
                            ├─── MikrotikError (code, message, target, details)
                            │
                            └─── MikrotikDeviceFacts (hostname, model, serial, version, uptime, cpu, memory)
```

## Core Models

### MikrotikTarget
Device configuration for a single MikroTik router.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| name | string | Yes | — | Unique device identifier |
| host | string | Yes | — | IP address or hostname |
| port | int | No | 8728 | REST API port |
| username | string | No | admin | REST API username |
| password | string | No | "" | REST API password |
| use_https | bool | No | false | Use HTTPS transport |
| tls_skip_verify | bool | No | false | Skip TLS cert verification |
| timeout | int | No | 60 | Request timeout in seconds |
| version | string | No | None | RouterOS version override |

### MikrotikDeviceInventory
Container for all device targets.

| Field | Type | Description |
|-------|------|-------------|
| devices | dict[str, MikrotikTarget] | Device name → Target mapping |

### MikrotikErrorCode
Enumeration of error types.

| Value | Description |
|-------|-------------|
| CONNECTION_ERROR | Cannot connect to device |
| TLS_ERROR | TLS/SSL handshake failure |
| AUTH_ERROR | Authentication failed |
| PATH_ERROR | REST API path not found |
| API_ERROR | General API error |
| ITSM_ERROR | ServiceNow CR validation failed |
| TIMEOUT_ERROR | Request timed out |
| DEVICE_NOT_FOUND | Device not in inventory |
| BLOCKED_OPERATION | Operation blocked by safety rules |
| VALIDATION_ERROR | Invalid input parameters |

### MikrotikError
Structured error envelope (credentials never appear in messages).

| Field | Type | Description |
|-------|------|-------------|
| code | MikrotikErrorCode | Error classification |
| message | string | Human-readable message |
| target | string? | Device name (optional) |
| details | string? | Additional details (optional) |
| timestamp | string | ISO timestamp |

### MikrotikApiResponse
HTTP response from MikroTik REST API.

| Field | Type | Description |
|-------|------|-------------|
| target | string | Device name |
| timestamp | string | ISO timestamp |
| path | string | REST API path |
| method | string | HTTP method |
| status_code | int | HTTP status code |
| data | list[dict] | Response data |
| success | bool | Operation success flag |
| error | MikrotikError? | Error object (if failed) |
| duration_ms | int? | Request duration |

### MikrotikDeviceFacts
Device information from /rest/system/resource and /rest/system/identity.

| Field | Type | Description |
|-------|------|-------------|
| target | string | Device name |
| hostname | string | Device hostname |
| model | string | Hardware model |
| serial_number | string | Serial number |
| version | string | RouterOS version |
| board_name | string | Board name |
| uptime | string | Uptime |
| cpu_load | string | CPU load % |
| memory_used | string | Memory used (bytes) |
| memory_total | string | Total memory (bytes) |
| disk_used | string | Disk used |
| disk_total | string | Total disk |
| architecture_name | string | CPU architecture |
| platform | string | Platform name |

### MikrotikConfigDiff
Configuration diff result.

| Field | Type | Description |
|-------|------|-------------|
| target | string | Device name |
| path | string | Config path |
| current | list[dict] | Current config |
| history | list[dict] | Historical config |
| added | list[dict] | Added entries |
| removed | list[dict] | Removed entries |
| modified | list[dict] | Modified entries |

### ItsmsGateResult
ServiceNow CR validation result.

| Field | Type | Description |
|-------|------|-------------|
| valid | bool | CR is valid and approved |
| cr_number | string | CR number |
| state | string | CR state |
| message | string | Validation message |
| bypassed | bool | True if NETCLAW_LAB_MODE |

### TemplateRenderResult
Jinja2 template rendering result.

| Field | Type | Description |
|-------|------|-------------|
| rendered_config | string | Rendered configuration |
| targets | list[str] | Target routers |
| dry_run | bool | Was this a dry run? |
| operations_planned | list[str] | Commands to be executed |
| success | bool | Render success |
| error | string? | Error message if failed |

## REST API Response Format

All GET endpoints return arrays of objects:

```json
[
  {
    ".id": "*1",
    "address": "10.0.0.1/24",
    "interface": "ether1",
    "disabled": "false",
    "dynamic": "false",
    "comment": ""
  }
]
```

- `.id` is always present (string like `*1`, `*2`)
- All values are strings (RouterOS convention)
- Empty fields may be omitted or empty string
