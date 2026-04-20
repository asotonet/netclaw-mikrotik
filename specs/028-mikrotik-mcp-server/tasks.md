# Implementation Tasks: MikroTik MCP Server

**Feature**: 028-mikrotik-mcp-server | **Date**: 2026-04-20

## Phase 1: Core Infrastructure

- [x] T001: Create spec directory structure (specs/028-mikrotik-mcp-server/*)
- [x] T002: Create models.py with all Pydantic models
- [x] T003: Create mikrotik_client.py with REST API client
- [x] T004: Create itsm_gate.py for ServiceNow CR validation
- [x] T005: Create blocklists.py for safety features
- [x] T006: Create mikrotik_mcp_server.py with 10 FastMCP tools
- [x] T007: Create requirements.txt
- [x] T008: Create __init__.py
- [x] T009: Create Dockerfile
- [x] T010: Create .dockerignore

## Phase 2: Documentation

- [x] T020: Create spec.md with user stories
- [x] T021: Create research.md with API research
- [x] T022: Create data-model.md
- [x] T023: Create quickstart.md
- [x] T024: Create contracts/mcp-tools.md
- [x] T025: Create checklists/requirements.md
- [x] T026: Create tasks.md
- [x] T027: Create mcp-servers/mikrotik-mcp/README.md
- [x] T028: Create workspace/skills/mikrotik-network/SKILL.md

## Phase 3: Integration & Verification (Next)

- [ ] T030: Add to config/openclaw.json (MCP server registration)
- [ ] T031: Add to .env.example (environment variables)
- [ ] T032: Test basic connection to MikroTik device
- [ ] T033: Verify get_router_list returns devices without passwords
- [ ] T034: Verify gather_device_facts returns correct information
- [ ] T035: Verify execute_mikrotik_command works for show commands
- [ ] T036: Verify blocklist prevents destructive commands
- [ ] T037: Verify ITSM gate blocks without CR
- [ ] T038: Verify ITSM gate passes with valid CR (or lab mode)
- [ ] T039: Verify render_and_apply_j2_template dry_run works
- [ ] T040: Verify GAIT logging outputs structured JSON

## Dependencies

- fastmcp>=1.0.0
- requests>=2.31.0
- pydantic>=2.5.0
- jinja2>=3.1.0
- pyyaml>=6.0
- urllib3>=2.0.0

## Notes

- All tasks marked [x] are complete
- Phase 3 tasks require a live MikroTik device or mock server
- GAIT logging is emitted to stderr as structured JSON
- ITSM gate requires ServiceNow credentials for full testing
