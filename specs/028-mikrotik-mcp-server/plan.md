# Implementation Plan: MikroTik MCP Server

**Feature**: 028-mikrotik-mcp-server | **Date**: 2026-04-20

## Overview

Build a MikroTik RouterOS REST API MCP server following the established NetClaw patterns (JunOS skill + gNMI MCP server).

## Protocol Decision

**User confirmed**: REST API (HTTP/HTTPS on port 8728/8729), NOT SSH/NETCONF.

## Architecture

```
mcp-servers/mikrotik-mcp/
├── mikrotik_mcp_server.py   # FastMCP server with 10 tools
├── mikrotik_client.py       # REST API client (requests)
├── models.py                # Pydantic data models
├── itsm_gate.py             # ServiceNow CR validation
├── blocklists.py            # Destructive operation prevention
├── requirements.txt         # Dependencies
├── Dockerfile               # Container image
└── README.md                # Documentation

workspace/skills/mikrotik-network/
└── SKILL.md                 # Skill definition

specs/028-mikrotik-mcp-server/
├── spec.md                  # User stories & requirements
├── plan.md                  # This plan
├── research.md              # MikroTik REST API research
├── data-model.md            # Pydantic model inventory
├── quickstart.md            # Setup guide
├── contracts/
│   └── mcp-tools.md        # Tool contracts
├── checklists/
│   └── requirements.md      # Quality checklist
└── tasks.md                 # Task breakdown
```

## Implementation

### Phase 1: Core (Complete)
- Created Pydantic models (MikrotikTarget, MikrotikError, MikrotikApiResponse, etc.)
- Created REST client with full RouterOS v7 API coverage
- Created ITSM gate for ServiceNow CR validation
- Created blocklists for destructive command prevention
- Created 10 FastMCP tools matching JunOS skill pattern

### Phase 2: Documentation (Complete)
- Created spec.md with 5 user stories
- Created research.md with API research findings
- Created data-model.md with entity relationships
- Created quickstart.md with setup instructions
- Created contracts/mcp-tools.md with tool definitions
- Created SKILL.md following JunOS skill format
- Created README.md with full API coverage

### Phase 3: Integration (Pending)
- Register in config/openclaw.json
- Add to .env.example
- Test with live MikroTik device

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Protocol | REST API (HTTP/HTTPS) | User confirmed |
| Port | 8728 (HTTP) / 8729 (HTTPS) | RouterOS standard |
| Auth | HTTP Basic Auth | RouterOS REST API standard |
| Inventory | JSON file (devices.json) | Matches JunOS pattern |
| Transport | stdio (FastMCP) | Standard NetClaw |
| ITSM gate | ServiceNow CR for writes | Matches gNMI/JunOS |
| Safety | blocklists.py (cmd + cfg) | Matches JunOS |
| GAIT | Structured JSON to stderr | Matches gNMI |

## API Coverage

Based on RouterOS REST API OpenAPI spec v7.22.1 from tikoci/restraml:
- IP: /ip/address, /ip/route, /ip/firewall/*, /ip/dhcp-server, etc.
- Routing: /routing/bgp/*, /routing/ospf/*, /routing/rip, /routing/isis, etc.
- Interface: /interface/ethernet, /interface/bridge, /interface/vlan, /interface/bonding, etc.
- PPP: /ppp/secret, /ppp/profile, /ppp/active
- User: /user, /user/active, /user/group, /user/ssh-keys
- System: /system/resource, /system/identity, /system/history
- Terminal: /rest/terminal/sync (CLI execution)

## Verification

1. Start MCP server: `python mikrotik_mcp_server.py`
2. List devices: `get_router_list`
3. Get facts: `gather_device_facts("router-name")`
4. Get config: `get_mikrotik_config("router-name", "/ip/address")`
5. Execute command: `execute_mikrotik_command("router-name", "/system resource print")`
6. Verify GAIT logs appear in stderr

## Constitution Principles

| Principle | Status |
|-----------|--------|
| I (Safety-First) | ✓ Blocklists + ITSM gate |
| II (Read-Before-Write) | ✓ Baseline before changes |
| III (Least Privilege) | ✓ Basic Auth, no SSH keys |
| IV (Audit Everything) | ✓ GAIT logging |
| V (Fail Closed) | ✓ ITSM gate required |
| VI (Idempotent Ops) | ✓ REST semantics |
| VII (Observable) | ✓ GAIT + structured errors |
| VIII (Verify After Change) | ✓ Post-change verification |
