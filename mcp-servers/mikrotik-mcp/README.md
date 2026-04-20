# MikroTik RouterOS REST API MCP Server

A FastMCP server providing MikroTik RouterOS management as MCP tools for NetClaw. Supports RouterOS v7 REST API on HTTP/HTTPS (port 8728/8729) with Basic Authentication.

**Based on RouterOS REST API OpenAPI spec v7.22.1** — All endpoints from MikroTik's official REST API are supported.

## Tools (18)

| # | Tool | Description | Safety |
|---|------|-------------|--------|
| 1 | `get_router_list` | List all configured MikroTik devices (passwords filtered) | Read-only |
| 2 | `add_device` | Add a new MikroTik device to inventory | Read-only |
| 3 | `reload_devices` | Reload device inventory from JSON file | Read-only |
| 4 | `execute_mikrotik_command` | Execute CLI command via REST API terminal | Blocklist |
| 5 | `execute_mikrotik_command_batch` | Execute command on multiple routers in parallel | Blocklist |
| 6 | `get_mikrotik_config` | Retrieve configuration via REST API | Read-only |
| 7 | `mikrotik_config_diff` | Compare config against history | Read-only |
| 8 | `load_and_commit_config` | Apply config changes (PUT/PATCH/DELETE) | ITSM-gated |
| 9 | `render_and_apply_j2_template` | Jinja2 template rendering + apply | ITSM-gated |
| 10 | `gather_device_facts` | Get device info: model, serial, version, uptime | Read-only |
| 11 | `backup_save` | Create local backup file on the router | Read-only |
| 12 | `config_export` | Export configuration as .rsc script text | Read-only |
| 13 | `system_monitor` | Monitor CPU, memory, disk I/O over duration | Read-only |
| 14 | `interface_monitor` | Monitor interface rx/tx bytes, packets, errors | Read-only |
| 15 | `queue_monitor` | Monitor queue (QoS) tx/rx rates and bytes | Read-only |
| 16 | `netwatch_list` | List all NetWatch hosts and status | Read-only |
| 17 | `netwatch_add` | Add NetWatch host to monitor via ping | ITSM-gated |
| 18 | `logging_config` | Get logging rules, topics, destinations | Read-only |

## Transport

**stdio** — FastMCP over standard input/output (JSON-RPC).

## RouterOS REST API Coverage

Full coverage of RouterOS v7 REST API paths (from OpenAPI spec v7.22.1):

### IP
`/ip/address`, `/ip/route`, `/ip/arp`, `/ip/dhcp-client`, `/ip/dhcp-server`, `/ip/dns`, `/ip/firewall/*`, `/ip/hotspot`, `/ip/ipsec`, `/ip/neighbor`, `/ip/pool`, `/ip/proxy`, `/ip/service`, `/ip/settings`, `/ip/smb`, `/ip/socks`, `/ip/ssh`, `/ip/tftp`, `/ip/traffic-flow`, `/ip/upnp`, `/ip/vrf`

### IPv6
`/ipv6/address`, `/ipv6/dhcp-client`, `/ipv6/dhcp-server`, `/ipv6/dns`, `/ipv6/firewall`, `/ipv6/nd`, `/ipv6/route`

### Routing
`/routing/bgp/*`, `/routing/ospf/*`, `/routing/rip`, `/routing/isis`, `/routing/pimsm`, `/routing/bfd`, `/routing/igmp-proxy`, `/routing/rpki`, `/routing/filter`, `/routing/route`, `/routing/table`

### Interface
`/interface`, `/interface/ethernet`, `/interface/bridge`, `/interface/vlan`, `/interface/bonding`, `/interface/vrrp`, `/interface/vxlan`, `/interface/gre`, `/interface/gre6`, `/interface/ovpn-*`, `/interface/l2tp-*`, `/interface/pppoe-*`, `/interface/pptp-*`, `/interface/sstp-*`, `/interface/wireguard`, `/interface/wifi`, `/interface/lte`, `/interface/macsec`

### PPP
`/ppp/secret`, `/ppp/profile`, `/ppp/active`, `/ppp/aaa`, `/ppp/l2tp-secret`

### User
`/user`, `/user/active`, `/user/group`, `/user/ssh-keys`

### System
`/system/resource`, `/system/identity`, `/system/history`, `/system/backup`, `/system/script`, `/system/scheduler`, `/system/package`, `/system/log`, `/system/clock`, `/system/health`, `/system/leds`, `/system/license`, `/system/logging`, `/system/ntp`

### Certificate
`/certificate`, `/certificate/crl`, `/certificate/scep-server`

### Tool
`/tool/ping`, `/tool/traceroute`, `/tool/bandwidth-test`, `/tool/sniffer`, `/tool/netwatch`, `/tool/fetch`, `/tool/mac-scan`, `/tool/ip-scan`

### Queue, SNMP, RADIUS
`/queue/*`, `/snmp/*`, `/radius/*`

### Terminal
`/rest/terminal/sync` — Execute CLI commands directly

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MIKROTIK_DEVICES_FILE` | `devices.json` | Path to device inventory JSON |
| `MIKROTIK_TIMEOUT` | `60` | Default request timeout in seconds |
| `NETCLAW_LAB_MODE` | `false` | Bypass ITSM gate (set to `true` for lab) |
| `SERVICENOW_INSTANCE_URL` | — | ServiceNow instance URL for CR validation |
| `SERVICENOW_API_KEY` | — | ServiceNow API key for CR validation |

## Device Inventory Format

Devices are defined in a `devices.json` file:

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

## Safety Features

### Command Blocklist
Blocks destructive CLI commands via `/rest/terminal/sync`:
- `/system/reboot`, `/system/shutdown`, `/system/reset-configuration`
- `/certificate/*/remove`, `/certificate/*/reset`
- `/file/remove`, `/file/export`
- `/user/*/remove`, `/user/*/disable`
- `/system/package/*/disable`, `/system/package/*/remove`
- `quit`, `exit`

### Config Blocklist
Blocks dangerous REST API operations:
- `/system/reset-configuration`, `/system/reboot`, `/system/shutdown`
- Certificate management paths
- User removal/disabling
- Interface disabling

### ITSM Gate
Configuration changes (PUT, PATCH, DELETE) require a ServiceNow Change Request:
- CR must be in `Implement` state
- Set `NETCLAW_LAB_MODE=true` to bypass for lab environments

## Installation

```bash
cd mcp-servers/mikrotik-mcp
pip install -r requirements.txt
```

## Quick Start

```bash
# Create devices.json with your MikroTik routers
python mikrotik_mcp_server.py -f devices.json

# Inside NetClaw:
# List devices
> get_router_list

# Gather facts
> gather_device_facts("core-mt-01")

# Get interface config
> get_mikrotik_config("core-mt-01", "/interface/ethernet")

# Get IP addresses
> get_mikrotik_config("core-mt-01", "/ip/address")

# Execute CLI command
> execute_mikrotik_command("core-mt-01", "/ip address print")

# Apply config change (requires CR)
> load_and_commit_config("core-mt-01", "/ip/address", "PUT", {"address": "192.168.1.1/24", "interface": "ether1"}, change_request_number="CHG0012345")
```

## Docker

```bash
docker build -t mikrotik-mcp .
docker run mikrotik-mcp
```

## Architecture

```
mikrotik-mcp/
├── mikrotik_mcp_server.py   # FastMCP server with 18 tools
├── mikrotik_client.py       # REST API client (requests)
├── models.py                # Pydantic data models
├── itsm_gate.py             # ServiceNow CR validation
├── blocklists.py            # Destructive operation prevention
├── requirements.txt
├── Dockerfile
└── README.md
```
