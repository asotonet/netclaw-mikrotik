---
name: mikrotik-network
description: "MikroTik RouterOS management via REST API — CLI execution, configuration management, Jinja2 template rendering, device facts, batch operations, real-time monitoring, NetWatch (18 tools). Use when managing MikroTik routers, pushing RouterOS configs, running show commands on RouterOS devices, or comparing config versions."
license: Apache-2.0
user-invocable: true
metadata: { "openclaw": { "requires": { "bins": ["python3"], "env": ["MIKROTIK_DEVICES_FILE"] } } }
---

# MikroTik RouterOS Network Automation

## MCP Server

| Field | Value |
|-------|-------|
| **Repository** | Built-in (netclaw-mikrotik/mcp-servers/mikrotik-mcp) |
| **Transport** | stdio (FastMCP) |
| **Python** | 3.10+ |
| **Protocol** | REST API (HTTP/HTTPS, port 8728/8729) |
| **API Version** | RouterOS v7 REST API (tested against v7.22.1) |
| **Dependencies** | fastmcp, requests, pydantic, jinja2, pyyaml |
| **Install** | `pip install -r mcp-servers/mikrotik-mcp/requirements.txt` |
| **Entry Point** | `python mcp-servers/mikrotik-mcp/mikrotik_mcp_server.py` |

## Device Inventory

Devices are defined in a `devices.json` file (not environment variables):

```json
{
  "core-mt-01": {
    "host": "10.0.0.1",
    "port": 8728,
    "username": "admin",
    "password": "changeme",
    "use_https": false,
    "tls_skip_verify": false
  },
  "edge-mt-02": {
    "host": "10.0.0.2",
    "port": 8729,
    "username": "admin",
    "password": "changeme",
    "use_https": true,
    "tls_skip_verify": true
  }
}
```

SSH key authentication is not supported — RouterOS REST API uses HTTP Basic Auth. Use strong passwords or session cookies in production.

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MIKROTIK_DEVICES_FILE` | `devices.json` | Path to device inventory JSON |
| `MIKROTIK_TIMEOUT` | `60` | Default command timeout in seconds |
| `NETCLAW_LAB_MODE` | `false` | Bypass ITSM gate for lab |
| `SERVICENOW_INSTANCE_URL` | — | ServiceNow for CR validation |
| `SERVICENOW_API_KEY` | — | ServiceNow API key |

---

## Tools (18)

### Device Inventory (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_router_list` | — | List all available MikroTik routers (passwords filtered from output) |
| `add_device` | `device_name?`, `device_ip?`, `device_port?`, `username?`, `password?`, `use_https?`, `tls_skip_verify?` | Add a new MikroTik device interactively |
| `reload_devices` | `file_name` | Reload the device dictionary from a new JSON file |

### CLI Execution (2 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `execute_mikrotik_command` | `router_name`, `command`, `timeout?` | Execute a RouterOS CLI command via /rest/terminal/sync |
| `execute_mikrotik_command_batch` | `router_names`, `command`, `timeout?` | Execute the same command on multiple routers in parallel |

### Configuration Management (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_mikrotik_config` | `router_name`, `config_path`, `params?` | Retrieve running config via targeted REST reads |
| `mikrotik_config_diff` | `router_name`, `history_index?` | Compare current config against history version |
| `load_and_commit_config` | `router_name`, `config_path`, `method`, `data?`, `entity_id?`, `change_request_number?`, `commit_comment?` | Apply config changes via REST PUT/PATCH/DELETE (ITSM-gated) |

### Template & Facts (2 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `render_and_apply_j2_template` | `template_content`, `vars_content`, `router_name?`, `router_names?`, `change_request_number?`, `commit_comment?`, `dry_run?` | Render Jinja2 template with YAML variables; optionally apply to one or many routers with dry-run support |
| `gather_device_facts` | `router_name`, `timeout?` | Gather device facts: hostname, model, serial, version, uptime, CPU, memory via /rest/system/resource and /rest/system/identity |

### Backup & Export (2 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `backup_save` | `router_name`, `backup_name?`, `password?` | Create a local backup file on the router |
| `config_export` | `router_name`, `compact?` | Export configuration as a script (.rsc text format) |

### Real-Time Monitoring (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `system_monitor` | `router_name`, `duration?` | Monitor CPU, memory, disk I/O over a duration (e.g., "30s") |
| `interface_monitor` | `router_name`, `interface_name?`, `duration?` | Monitor interface rx/tx bytes, packets, errors |
| `queue_monitor` | `router_name`, `duration?` | Monitor queue (QoS) tx/rx rates and bytes |

### NetWatch & Logging (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `netwatch_list` | `router_name` | List all NetWatch hosts and their status |
| `netwatch_add` | `router_name`, `host`, `interval?`, `timeout?`, `up_script?`, `down_script?`, `comment?` | Add a NetWatch host to monitor via ping |
| `logging_config` | `router_name` | Get logging configuration: rules, topics, and destinations |

---

## Supported REST API Paths

The MCP server supports ALL RouterOS v7 REST API paths (from OpenAPI spec v7.22.1):

### IP Management
`/ip/address`, `/ip/route`, `/ip/arp`, `/ip/dhcp-client`, `/ip/dhcp-server`, `/ip/dns`, `/ip/firewall/filter`, `/ip/firewall/nat`, `/ip/firewall/mangle`, `/ip/firewall/raw`, `/ip/firewall/address-list`, `/ip/hotspot`, `/ip/ipsec`, `/ip/neighbor`, `/ip/pool`, `/ip/proxy`, `/ip/service`, `/ip/settings`, `/ip/smb`, `/ip/socks`, `/ip/ssh`, `/ip/tftp`, `/ip/traffic-flow`, `/ip/upnp`, `/ip/vrf`

### Routing Protocols
`/routing/bgp/connection`, `/routing/bgp/session`, `/routing/bgp/instance`, `/routing/bgp/template`, `/routing/bgp/evpn`, `/routing/bgp/vpls`, `/routing/bgp/vpn`, `/routing/ospf/area`, `/routing/ospf/instance`, `/routing/ospf/interface`, `/routing/ospf/neighbor`, `/routing/ospf/lsa`, `/routing/rip`, `/routing/isis`, `/routing/pimsm`, `/routing/bfd`, `/routing/igmp-proxy`, `/routing/rpki`, `/routing/route`, `/routing/table`

### Interface Management
`/interface`, `/interface/ethernet`, `/interface/bridge`, `/interface/bridge/port`, `/interface/bridge/vlan`, `/interface/bridge/filter`, `/interface/bridge/nat`, `/interface/vlan`, `/interface/bonding`, `/interface/vrrp`, `/interface/vxlan`, `/interface/gre`, `/interface/gre6`, `/interface/ipip`, `/interface/ipipv6`, `/interface/eoip`, `/interface/ovpn-client`, `/interface/ovpn-server`, `/interface/l2tp-client`, `/interface/l2tp-server`, `/interface/pppoe-client`, `/interface/pppoe-server`, `/interface/pptp-client`, `/interface/pptp-server`, `/interface/sstp-client`, `/interface/sstp-server`, `/interface/wireguard`, `/interface/wireguard/peers`, `/interface/wifi`, `/interface/lte`, `/interface/macsec`, `/interface/macvlan`, `/interface/mesh`

### PPP / VPN
`/ppp/secret`, `/ppp/profile`, `/ppp/active`, `/ppp/aaa`, `/ppp/l2tp-secret`

### User Management
`/user`, `/user/active`, `/user/group`, `/user/ssh-keys`

### System
`/system/resource`, `/system/identity`, `/system/history`, `/system/backup`, `/system/script`, `/system/scheduler`, `/system/package`, `/system/log`, `/system/clock`, `/system/health`, `/system/leds`, `/system/license`, `/system/logging`, `/system/ntp`, `/system/reboot`, `/system/shutdown`

### Certificate
`/certificate`, `/certificate/crl`, `/certificate/scep-server`

### Diagnostic Tools
`/tool/ping`, `/tool/traceroute`, `/tool/bandwidth-test`, `/tool/sniffer`, `/tool/netwatch`, `/tool/fetch`, `/tool/mac-scan`, `/tool/ip-scan`

### Queue / SNMP / RADIUS
`/queue/simple`, `/queue/tree`, `/queue/interface`, `/snmp`, `/radius`

---

## Safety Features

### Command Blocklist (`blocklists.py`)
The server prevents destructive CLI commands via /rest/terminal/sync:
- `request system reboot`
- `request system shutdown`
- `request system reset-configuration`
- `certificate/*/remove`
- `file/remove`, `file/export`
- `user/*/remove`, `user/*/disable`
- `system/package/*/disable`, `system/package/*/remove`
- `quit`, `exit`

### Configuration Blocklist
Prevents dangerous REST API operations:
- `/system/reset-configuration`, `/system/reboot`, `/system/shutdown`
- Certificate management
- User removal/disabling
- Interface disabling

### Credential Filtering
`get_router_list` automatically strips passwords before returning device data.

---

## Workflows

### 1. MikroTik Device Discovery
```
get_router_list → inventory all available MikroTik routers
→ gather_device_facts(router) per device → hostname, model, serial, version, uptime
→ Cross-reference with NetBox/Nautobot → flag discrepancies
→ GAIT
```

### 2. MikroTik Health Check
```
get_router_list → identify target routers
→ execute_mikrotik_command_batch(routers, "/system resource print") → CPU/memory
→ execute_mikrotik_command_batch(routers, "/interface print") → interface status
→ execute_mikrotik_command_batch(routers, "/ip address print") → IP addressing
→ execute_mikrotik_command_batch(routers, "/routing bgp session print") → BGP peer health
→ execute_mikrotik_command_batch(routers, "/routing ospf neighbor print") → OSPF neighbor health
→ Severity-sort findings → GAIT
```

### 3. MikroTik Configuration Audit
```
get_router_list → select target routers
→ get_mikrotik_config(router, "/ip/address") → current IP config
→ get_mikrotik_config(router, "/ip/route") → routing table
→ get_mikrotik_config(router, "/ip/firewall/filter") → firewall rules
→ get_mikrotik_config(router, "/routing/bgp/session") → BGP config
→ Compare against golden config templates → flag deviations
→ GAIT
```

### 4. MikroTik Configuration Deployment
```
ServiceNow CR must be in Implement state
→ get_mikrotik_config(router, "/ip/address") → baseline current config
→ render_and_apply_j2_template(template, vars, router, dry_run=true) → preview changes
→ render_and_apply_j2_template(template, vars, router, apply_config=true, commit_comment="CR-12345") → apply
→ get_mikrotik_config(router, "/ip/address") → verify post-change config
→ execute_mikrotik_command(router, "/ip address print") → verify addressing
→ GAIT
```

### 5. MikroTik Batch Operations
```
get_router_list → filter to target group (e.g., all edge routers)
→ execute_mikrotik_command_batch(routers, "/system identity print") → identity check
→ execute_mikrotik_command_batch(routers, "/routing ospf neighbor print") → protocol health
→ execute_mikrotik_command_batch(routers, "/ip route print where gateway!=\"\"") → routes with gateways
→ Aggregate results → severity-sort → GAIT
```

### 6. MikroTik Config Diff Investigation
```
mikrotik_config_diff(router, history_index=0) → compare against most recent history entry
→ mikrotik_config_diff(router, history_index=1) → compare against version before that
→ Identify what changed, when, and the impact
→ execute_mikrotik_command(router, "/system history print") → commit history
→ GAIT
```

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **netbox-reconcile** | Cross-reference MikroTik device facts (model, serial, version) against NetBox source of truth |
| **nautobot-sot** | Same as NetBox — validate MikroTik device IPAM data in Nautobot |
| **infrahub-sot** | Cross-reference Infrahub node data with MikroTik device inventory |
| **itential-automation** | Itential workflows can orchestrate MikroTik config deployments |
| **servicenow-change-workflow** | Gate all MikroTik config commits behind ServiceNow Change Requests |
| **gait-session-tracking** | Every MikroTik command, config push, and batch operation logged in GAIT |
| **nso-device-ops** | NSO for multi-vendor orchestration, MikroTik MCP for direct MikroTik access |
| **nvd-cve** | Scan RouterOS versions against NVD vulnerability database |
| **canvas-network-viz** | Visualize MikroTik network topology via Canvas/A2UI |

---

## Guardrails

- **Always call `get_router_list` first** — verify the target device exists before executing commands
- **Always baseline before changes** — call `get_mikrotik_config` before any `load_and_commit_config` or template apply
- **Use dry_run for templates** — set `dry_run=true` on `render_and_apply_j2_template` to preview changes before committing
- **Gate config changes** — all `load_and_commit_config` and `render_and_apply_j2_template(apply_config=true)` calls must have a ServiceNow CR in `Implement` state
- **Use batch for fleet ops** — prefer `execute_mikrotik_command_batch` over looping `execute_mikrotik_command` for multi-router operations
- **Set reasonable timeouts** — default is 60s; reduce for simple show commands, increase for large config operations
- **Include commit comments** — always provide a `commit_comment` referencing the ServiceNow CR number
- **Verify after config pushes** — call `get_mikrotik_config` and protocol-specific show commands after changes
- **Respect the blocklists** — `blocklists.py` prevents destructive operations; do not bypass them
- **Record in GAIT** — every command, config push, batch operation, and template rendering must be logged

---

## Key Differences from JunOS Skill

| Capability | MikroTik (this skill) | JunOS (junos-network) |
|-----------|----------------------|----------------------|
| **Protocol** | REST API (HTTP/HTTPS) | SSH/NETCONF via PyEZ |
| **Vendor** | MikroTik RouterOS | Juniper JunOS |
| **CLI Execution** | `execute_mikrotik_command` via `/rest/terminal/sync` | `execute_junos_command` via NETCONF |
| **Config Retrieval** | `get_mikrotik_config` via targeted REST reads | `get_junos_config` via NETCONF |
| **Config Push** | `load_and_commit_config` via REST PUT/PATCH/DELETE | `load_and_commit_config` via NETCONF |
| **Device Facts** | `gather_device_facts` via `/rest/system/resource` | `gather_device_facts` via PyEZ facts |
| **Config Diff** | `mikrotik_config_diff` via history API | `junos_config_diff` via rollback compare |
| **Safety** | blocklists.py (command + config) | block.cmd + block.cfg (regex) |
| **MCP Tools** | 18 | 10 |
