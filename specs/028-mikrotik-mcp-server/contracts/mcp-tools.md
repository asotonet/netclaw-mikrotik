# MCP Tool Contracts: MikroTik MCP Server

**Feature**: 028-mikrotik-mcp-server | **Date**: 2026-04-20
**Transport**: stdio
**Protocol**: MCP (Model Context Protocol) via FastMCP

## Tools

---

### 1. get_router_list

**Description**: List all configured MikroTik routers with connection info. Passwords and SSH keys are automatically filtered from output.

**Parameters**: None

**Returns**: JSON object with device count and array of device info (no credentials).

**Safety**: Read-only. No ITSM gate required.

**GAIT**: Logs operation `mikrotik_list_devices` with device_count and device list.

---

### 2. add_device

**Description**: Add a new MikroTik device to the inventory (writes to devices.json).

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| device_name | string | Yes | — | Unique device identifier |
| device_ip | string | Yes | — | IP address or hostname |
| device_port | int | No | 8728 | REST API port |
| username | string | No | admin | REST API username |
| password | string | No | "" | REST API password |
| use_https | bool | No | false | Use HTTPS |
| tls_skip_verify | bool | No | false | Skip TLS verification |
| devices_file | string | No | devices.json | Inventory file path |

**Returns**: JSON confirmation with added device info (password filtered).

**Safety**: Read-only (inventory write only). No ITSM gate required.

**GAIT**: Logs operation `mikrotik_add_device` with device name, host, port, use_https.

---

### 3. reload_devices

**Description**: Reload device inventory from a JSON file. Use after manually editing devices.json.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| devices_file | string | No | devices.json | Path to devices inventory |

**Returns**: JSON with loaded device count and device names.

**Safety**: Read-only (in-memory reload). No ITSM gate required.

**GAIT**: Logs operation `mikrotik_reload_devices` with device_count and devices_file.

---

### 4. execute_mikrotik_command

**Description**: Execute a MikroTik CLI command via REST API terminal. Supports all RouterOS CLI commands.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| router_name | string | Yes | — | Target device name |
| command | string | Yes | — | CLI command (e.g., "/ip address print") |
| timeout | int | No | 60 | Command timeout in seconds |

**Returns**: JSON with command output (array of result objects).

**Safety**: Blocklist prevents destructive commands (reboot, shutdown, etc.).

**GAIT**: Logs operation `mikrotik_command` with router, command, success, blocked.

**Error Codes**:
- `DEVICE_NOT_FOUND`: Router not in inventory
- `BLOCKED_OPERATION`: Command matches blocklist
- `CONNECTION_ERROR`: Cannot reach device
- `AUTH_ERROR`: Authentication failed
- `TIMEOUT_ERROR`: Command timed out

---

### 5. execute_mikrotik_command_batch

**Description**: Execute the same CLI command on multiple MikroTik routers in parallel (thread pool, max 10 workers).

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| router_names | string[] | Yes | — | List of target device names |
| command | string | Yes | — | CLI command to execute |
| timeout | int | No | 60 | Per-device timeout in seconds |

**Returns**: JSON with per-device results (success/failure per router).

**Safety**: Blocklist prevents destructive commands.

**GAIT**: Logs operation `mikrotik_command_batch` with routers, command, device_count, success_count.

**Error Handling**: Individual router failures do not fail entire batch. Each router returns its own success/failure.

---

### 6. get_mikrotik_config

**Description**: Retrieve running configuration from MikroTik via targeted REST API reads. More structured than CLI output.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| router_name | string | Yes | — | Target device name |
| config_path | string | Yes | — | REST API path (e.g., "/ip/address") |
| params | object | No | — | Query parameters for filtering |

**Returns**: JSON array of configuration entries.

**Supported paths include**:
- `/ip/address`, `/ip/route`, `/ip/firewall/filter`, `/ip/firewall/nat`
- `/routing/bgp/session`, `/routing/ospf/neighbor`, `/routing/rip`
- `/interface/ethernet`, `/interface/bridge`, `/interface/vlan`
- `/ppp/secret`, `/user`, `/system/resource`, `/system/identity`
- And all other RouterOS REST API paths

**Safety**: Read-only. No ITSM gate required.

**GAIT**: Logs operation `mikrotik_get_config` with router, path, success, record_count.

---

### 7. mikrotik_config_diff

**Description**: Compare current configuration against a historical version from /rest/system/history.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| router_name | string | Yes | — | Target device name |
| history_index | int | No | 0 | History entry index (0=most recent) |

**Returns**: JSON with added, removed, modified entries.

**Safety**: Read-only. No ITSM gate required.

**GAIT**: Logs operation `mikrotik_config_diff` with router, history_index, success.

---

### 8. load_and_commit_config

**Description**: Apply configuration changes to MikroTik via REST API (PUT/PATCH/DELETE). REQUIRES ServiceNow Change Request in production.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| router_name | string | Yes | — | Target device name |
| config_path | string | Yes | — | REST API path (e.g., "/ip/address") |
| method | string | Yes | — | HTTP method: PUT (create), PATCH (update), DELETE (delete) |
| data | object | No | — | JSON body for PUT/PATCH |
| entity_id | string | No | — | Entity ID for PATCH/DELETE (e.g., "*1") |
| change_request_number | string | No | — | ServiceNow CR (required in production) |
| commit_comment | string | No | — | Comment describing the change |

**Returns**: JSON confirmation of applied changes.

**Safety**: WRITE operation. ITSM-gated. Config blocklist enforced.

**GAIT**: Logs operation `mikrotik_load_commit` with router, path, method, CR, success, comment.

**Error Codes**:
- `ITSM_ERROR`: CR validation failed or not provided
- `BLOCKED_OPERATION`: Config change matches blocklist
- `DEVICE_NOT_FOUND`: Router not in inventory
- `CONNECTION_ERROR`: Cannot reach device
- `AUTH_ERROR`: Authentication failed

---

### 9. render_and_apply_j2_template

**Description**: Render a Jinja2 configuration template with YAML variables and optionally apply to MikroTik routers.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| template_content | string | Yes | — | Jinja2 template content |
| vars_content | string | Yes | — | YAML variables |
| router_name | string | No | — | Single target device |
| router_names | string[] | No | — | Multiple target devices |
| change_request_number | string | No | — | CR (required if dry_run=false) |
| commit_comment | string | No | — | Commit comment |
| dry_run | bool | No | true | Preview without applying |

**Returns**: JSON with rendered config and planned/executed operations.

**YAML vars example**:
```yaml
hostname: core-mt-01
wan_interface: ether1
wan_ip: 192.168.1.1/24
```

**Template example**:
```jinja2
/ip address add address={{ wan_ip }} interface={{ wan_interface }}
/interface bridge add name=bridge-LAN
```

**Safety**: ITSM-gated for apply mode. Command blocklist enforced per line.

**GAIT**: Logs operation `mikrotik_render_template` with targets, command_count, cr, dry_run, success.

---

### 10. gather_device_facts

**Description**: Gather device facts: hostname, model, serial, version, uptime, CPU load, memory usage from /rest/system/resource and /rest/system/identity.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| router_name | string | Yes | — | Target device name |
| timeout | int | No | 60 | Request timeout in seconds |

**Returns**: JSON with device facts object.

**Safety**: Read-only. No ITSM gate required.

**GAIT**: Logs operation `mikrotik_gather_facts` with router, hostname, model, version, success.
