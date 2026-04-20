# Quickstart: MikroTik RouterOS MCP Server

**Feature**: 028-mikrotik-mcp-server | **Date**: 2026-04-20

## Prerequisites

- Python 3.10+
- MikroTik router running RouterOS v7 with REST API enabled
- Network connectivity to MikroTik REST API port (8728/8729)
- MikroTik username/password for REST API access

## 1. Install Dependencies

```bash
cd netclaw-mikrotik
pip install -r mcp-servers/mikrotik-mcp/requirements.txt
```

## 2. Configure Device Inventory

Create a `devices.json` file with your MikroTik routers:

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

**Security note**: Use strong passwords. Consider creating a read-only API user for monitoring. Use HTTPS in production.

## 3. Enable REST API on MikroTik

On your MikroTik router:

```
/ip service enable api-ssl
# Or for HTTP (not recommended for production):
/ip service enable api
```

Configure access:

```
/ip service api-ssl set port=8729
/ip service api-ssl set certificate=your-cert
/ip firewall filter add chain=input protocol=tcp dst-port=8729 action=accept
```

## 4. Register in OpenClaw

Add to `config/openclaw.json`:

```json
{
  "mcpServers": {
    "mikrotik-mcp": {
      "command": "python",
      "args": ["mcp-servers/mikrotik-mcp/mikrotik_mcp_server.py"],
      "env": {
        "MIKROTIK_DEVICES_FILE": "devices.json"
      }
    }
  }
}
```

## 5. Set Environment Variables (Optional)

```bash
# Device inventory file
export MIKROTIK_DEVICES_FILE=devices.json

# Default timeout (seconds)
export MIKROTIK_TIMEOUT=60

# Lab mode (bypass ITSM gate)
export NETCLAW_LAB_MODE=true

# ServiceNow for ITSM gating (production)
export SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com
export SERVICENOW_API_KEY=your-api-key
```

## 6. Verify Connection

Test the MCP server:

```bash
python mcp-servers/mikrotik-mcp/mikrotik_mcp_server.py -f devices.json
```

Then in NetClaw:

```
> get_router_list
```

Expected: JSON array of your MikroTik devices with connection info.

## 7. Basic Operations

### List devices
```
> get_router_list
```

### Gather device facts
```
> gather_device_facts("core-mt-01")
```
Returns: hostname, model, serial, version, uptime, CPU, memory

### Get IP addresses
```
> get_mikrotik_config("core-mt-01", "/ip/address")
```

### Get BGP sessions
```
> get_mikrotik_config("core-mt-01", "/routing/bgp/session")
```

### Get firewall rules
```
> get_mikrotik_config("core-mt-01", "/ip/firewall/filter")
```

### Execute CLI command
```
> execute_mikrotik_command("core-mt-01", "/system resource print")
```

### Batch health check
```
> execute_mikrotik_command_batch(["core-mt-01", "edge-mt-02"], "/interface print")
```

### Add new device
```
> add_device("new-mt-03", "10.0.0.3", 8728, "admin", "password")
```

## 8. Configuration Changes

### Template-based deployment (recommended)

```yaml
# vars.yaml
hostname: core-mt-01
wan_interface: ether1
wan_ip: 192.168.1.1/24
lan_interface: bridge-LAN
lan_network: 10.0.10.0/24
```

```jinja2
# template.rsc
/ip address add address={{ wan_ip }} interface={{ wan_interface }} comment="WAN"
/interface bridge add name={{ lan_interface }} comment="LAN bridge"
/ip address add address={{ lan_network }} interface={{ lan_interface }} comment="LAN"
```

Dry run:
```
> render_and_apply_j2_template(template_content, vars_content, "core-mt-01", dry_run=true)
```

Apply (with CR in production):
```
> render_and_apply_j2_template(template_content, vars_content, "core-mt-01", change_request_number="CHG0012345", commit_comment="Add WAN/LAN config", dry_run=false)
```

### Direct config push

Add IP address:
```
> load_and_commit_config("core-mt-01", "/ip/address", "PUT", {"address": "192.168.1.1/24", "interface": "ether1"}, change_request_number="CHG0012345")
```

Modify firewall rule:
```
> load_and_commit_config("core-mt-01", "/ip/firewall/filter", "PATCH", {"disabled": "true"}, entity_id="*3", change_request_number="CHG0012345")
```

Delete NAT rule:
```
> load_and_commit_config("core-mt-01", "/ip/firewall/nat", "DELETE", entity_id="*5", change_request_number="CHG0012345")
```

## 9. Verify GAIT Logging

After any operation, verify GAIT audit trail:

```
> Show the latest GAIT session log entries
```

Expected: Entries with operation names: `mikrotik_list_devices`, `mikrotik_command`, `mikrotik_get_config`, `mikrotik_load_commit`, etc.

## Troubleshooting

### Connection refused
- Verify REST API is enabled: `/ip service print where name~"api"`
- Check firewall rules allow port 8728/8729
- Verify IP address is correct

### TLS errors
- For self-signed certs: set `tls_skip_verify: true` in devices.json
- Or import MikroTik cert to trusted root

### Authentication failed
- Verify username/password is correct
- Check user has REST API permission: `/user print`
- Try enabling api-ssl service: `/ip service enable api-ssl`

### Command blocked
- The command matches the blocklist (e.g., `/system reboot`)
- For lab/testing: set `NETCLAW_LAB_MODE=true` (note: bypasses ITSM gate)

### ITSM gate failures
- Verify ServiceNow credentials: `SERVICENOW_INSTANCE_URL` and `SERVICENOW_API_KEY`
- Verify CR is in "Implement" state
- For lab: `NETCLAW_LAB_MODE=true` bypasses validation
