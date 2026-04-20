# Requirements Checklist: MikroTik MCP Server

**Feature**: 028-mikrotik-mcp-server | **Date**: 2026-04-20

## Specification Quality

- [x] **User stories**: All 5 user stories documented in spec.md with acceptance criteria
- [x] **User story priority**: P1 for Device Discovery, Health Check, Config Retrieval; P2 for Config Deployment, Templates
- [x] **Independent testability**: Each user story has test scenarios that can be validated independently
- [x] **Why-priority**: Each story includes "Why this priority" explaining business value

## Functional Requirements

- [x] **10 MCP tools**: All tools defined in contracts/mcp-tools.md
  - [x] get_router_list (inventory)
  - [x] add_device (inventory)
  - [x] reload_devices (inventory)
  - [x] execute_mikrotik_command (CLI)
  - [x] execute_mikrotik_command_batch (CLI)
  - [x] get_mikrotik_config (config)
  - [x] mikrotik_config_diff (config)
  - [x] load_and_commit_config (config)
  - [x] render_and_apply_j2_template (template)
  - [x] gather_device_facts (facts)
- [x] **REST API coverage**: All major RouterOS v7 paths supported
- [x] **Device inventory**: JSON file-based inventory (devices.json)
- [x] **ITSM gate**: ServiceNow CR validation for config writes
- [x] **Safety blocklists**: Command and config blocklists implemented
- [x] **Credential filtering**: Passwords filtered from get_router_list output

## Non-Functional Requirements

- [x] **Protocol**: REST API (HTTP/HTTPS) — user confirmed
- [x] **Transport**: stdio via FastMCP
- [x] **Python**: 3.10+
- [x] **Dependencies**: fastmcp, requests, pydantic, jinja2, pyyaml (all in requirements.txt)
- [x] **GAIT logging**: All operations emit structured JSON to stderr
- [x] **Error taxonomy**: MikrotikErrorCode enum with 10 error types
- [x] **Pydantic models**: All request/response data modeled

## Documentation

- [x] **README.md**: Complete server documentation
- [x] **SKILL.md**: Skill documentation following JunOS pattern
- [x] **quickstart.md**: Setup and usage guide
- [x] **research.md**: MikroTik REST API research findings
- [x] **data-model.md**: Pydantic model inventory
- [x] **contracts/mcp-tools.md**: Tool contracts with parameters
- [x] **spec.md**: Feature specification with user stories
- [x] **plan.md**: Implementation plan

## Safety & Security

- [x] **Command blocklist**: Destructive CLI commands blocked
- [x] **Config blocklist**: Dangerous REST operations blocked
- [x] **ITSM gate**: ServiceNow CR validation for writes
- [x] **Lab mode bypass**: NETCLAW_LAB_MODE for testing
- [x] **Credential filtering**: No passwords in output
- [x] **Error sanitization**: Credentials never in error messages

## Architecture Patterns (following NetClaw conventions)

- [x] **Vendor dialect**: MikroTik-specific path defaults
- [x] **Environment-driven config**: MIKROTIK_DEVICES_FILE, MIKROTIK_TIMEOUT
- [x] **Decorator-based tools**: @mcp.tool() pattern
- [x] **ITSM as separate module**: itsm_gate.py
- [x] **Structured errors**: MikrotikError with error codes
- [x] **GAIT audit logging**: Structured JSON to stderr

## File Structure

- [x] mcp-servers/mikrotik-mcp/
  - [x] mikrotik_mcp_server.py
  - [x] mikrotik_client.py
  - [x] models.py
  - [x] itsm_gate.py
  - [x] blocklists.py
  - [x] requirements.txt
  - [x] Dockerfile
  - [x] README.md
  - [x] __init__.py
- [x] workspace/skills/mikrotik-network/
  - [x] SKILL.md
- [x] specs/028-mikrotik-mcp-server/
  - [x] spec.md
  - [x] plan.md
  - [x] research.md
  - [x] data-model.md
  - [x] quickstart.md
  - [x] contracts/mcp-tools.md
  - [x] checklists/requirements.md
  - [x] tasks.md

## OpenAPI Compliance

MikroTik REST API spec v7.22.1 from tikoci/restraml:
- [x] All IP paths supported (/ip/address, /ip/route, /ip/firewall/*, etc.)
- [x] All routing paths supported (/routing/bgp/*, /routing/ospf/*, etc.)
- [x] All interface paths supported (/interface/ethernet, /interface/bridge, etc.)
- [x] PPP, user, system, certificate, tool paths supported
- [x] Terminal CLI execution via /rest/terminal/sync
