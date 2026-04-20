# Research: MikroTik RouterOS REST API v7

**Feature**: 028-mikrotik-mcp-server | **Date**: 2026-04-20

## Research Summary

MikroTik RouterOS provides a REST API for device management starting from RouterOS v7.
The REST API is HTTP/JSON-based (not the legacy binary API protocol on port 8728/8729).

## Key Sources

- **Official REST API Docs**: https://help.mikrotik.com/docs/display/ROS/REST+API
- **OpenAPI Spec (v7.22.1)**: https://github.com/tikoci/restraml (community-generated, authoritative)
- **Community**: MikroTik Forum, RouterOS REST API discussions

## RouterOS REST API Characteristics

### Authentication
- **HTTP Basic Auth** with RouterOS username/password
- Session cookies also supported for extended sessions
- Default: username "admin", no password

### HTTP Methods Mapping
| Method | CRUD | Console Command | Purpose |
|--------|------|----------------|---------|
| GET | Read | print | Retrieve records |
| PATCH | Update | set | Modify single record |
| PUT | Create | add | Create new record |
| DELETE | Delete | remove | Delete record |
| POST | Universal | various | Access all console commands |

### Response Format
- **ECMA-404 JSON** standard
- All values returned as strings in JSON responses
- Returns arrays of objects with `.id` field (e.g., `*1`, `*2`)
- All values are strings — need type coercion in client

### Error Responses
```json
{"error":404,"message":"Not Found","detail":"..."}
{"error":406,"message":"Not Acceptable","detail":"no such command or directory"}
```
HTTP status 400+ for failures.

### Key REST Paths Discovered

**System**:
- `GET /rest/system/resource` — CPU, memory, disk, version info
- `GET /rest/system/identity` — Device hostname
- `GET /rest/system/history` — Configuration history
- `POST /rest/system/reboot` — Reboot device
- `POST /rest/export` — Export configuration

**IP**:
- `GET /rest/ip/address` — IP addresses
- `GET /rest/ip/route` — Routing table
- `GET /rest/ip/firewall/filter` — Firewall filter rules
- `GET /rest/ip/firewall/nat` — NAT rules
- `GET /rest/ip/dhcp-server/lease` — DHCP leases
- `GET /rest/ip/dhcp-server` — DHCP server config

**Routing**:
- `GET /rest/routing/bgp/session` — BGP sessions
- `GET /rest/routing/bgp/instance` — BGP instances
- `GET /rest/routing/ospf/area` — OSPF areas
- `GET /rest/routing/ospf/neighbor` — OSPF neighbors
- `GET /rest/routing/rip` — RIP config
- `GET /rest/routing/isis` — IS-IS config

**Interface**:
- `GET /rest/interface` — All interfaces
- `GET /rest/interface/ethernet` — Ethernet interfaces
- `GET /rest/interface/bridge` — Bridge interfaces
- `GET /rest/interface/vlan` — VLAN interfaces
- `GET /rest/interface/bonding` — Bonding interfaces
- `GET /rest/interface/wireguard` — WireGuard tunnels

**PPP**:
- `GET /rest/ppp/secret` — PPP secrets (user accounts)
- `GET /rest/ppp/profile` — PPP profiles
- `GET /rest/ppp/active` — Active PPP connections

**User**:
- `GET /rest/user` — User accounts
- `GET /rest/user/active` — Active users
- `GET /rest/user/group` — User groups

**Terminal (CLI)**:
- `POST /rest/terminal/sync` — Execute CLI command
  - Body: `{"command": "/ip address print"}`
  - Returns: Array of result objects

## Important Notes

### Port Differences
- **Binary API**: TCP 8728 (unencrypted), 8729 (TLS)
- **REST API**: HTTP 8728, HTTPS 8729
- These are the same ports but different protocols!

### RouterOS Version Requirements
- REST API introduced in RouterOS v7
- Some paths require specific RouterOS versions
- CAPsMAN requires RouterOS 7.1+
- WireGuard requires RouterOS 7.1+

### Security Considerations
- HTTP Basic Auth sends password in clear (use HTTPS)
- Self-signed certificates common — need `tls_skip_verify` option
- API user permissions follow standard RouterOS user model
- Consider creating dedicated API read-only user for monitoring

### Performance Notes
- 60-second timeout default
- Large config exports can be slow
- Consider pagination for large rule sets
- Batch operations use thread pool (max 10 workers)

## Libraries Considered

1. **requests** — Chosen. Simple HTTP client, widely used.
2. **httpx** — Alternative, supports async. Not needed for stdio MCP.
3. **py routeros-api** — Legacy binary API, not REST.

## Implementation Decision

**Chosen approach**: Custom client using `requests` library.

**Rationale**:
- No official MikroTik REST API Python SDK
- Community libraries incomplete or unmaintained
- `requests` is already in NetClaw's dependency tree
- Simple REST operations don't need a full SDK

**What we build**:
- `MikrotikClient` — HTTP client wrapping requests
- `MikrotikClientWrapper` — Manages multiple device clients
- `MikrotikTarget` — Device configuration model
- 10 FastMCP tools exposing core functionality
