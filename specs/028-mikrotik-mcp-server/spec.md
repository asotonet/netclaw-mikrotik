# Feature Specification: MikroTik RouterOS REST API MCP Server

**Feature Branch**: `028-mikrotik-mcp-server`
**Created**: 2026-04-20
**Status**: Draft
**Input**: User request to build MikroTik RouterOS management integration following JunOS skill patterns, based on RouterOS v7 REST API (confirmed protocol: REST API, not SSH/NETCONF).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - MikroTik Device Discovery (Priority: P1)

As a network engineer managing a mixed-vendor fleet including MikroTik routers,
I want to discover and inventory all MikroTik devices so I can verify their
presence, model, and software version before performing any operations.

**Why this priority**: Device discovery is the foundational first step for all
subsequent operations. Without knowing what MikroTik devices exist and their
basic facts (model, serial, version), no safe operations can be performed.

**Independent Test**: Can be fully tested by configuring a mock devices.json
with test device entries, calling get_router_list, and verifying password is
not in output. gather_device_facts can be tested against a real or mock
MikroTik REST API response.

**Acceptance Scenarios**:

1. **Given** a devices.json file with multiple MikroTik routers configured,
   **When** the operator calls `get_router_list`,
   **Then** the system returns all device names and connection info (IP, port, HTTPS)
   with passwords redacted, and the count matches the inventory.

2. **Given** a MikroTik router is reachable via REST API,
   **When** the operator calls `gather_device_facts("router-name")`,
   **Then** the system returns hostname, model, serial-number, version, uptime,
   CPU load, memory used/total from /rest/system/resource and /rest/system/identity.

3. **Given** a device name that does not exist in inventory,
   **When** the operator calls any tool with that device name,
   **Then** the system returns a DEVICE_NOT_FOUND error without attempting connection.

4. **Given** the devices.json file is empty or missing,
   **When** the operator calls `get_router_list`,
   **Then** the system returns an empty list with success=True.

---

### User Story 2 - MikroTik Health Check (Priority: P1)

As a network engineer performing routine health checks on MikroTik routers,
I want to execute show commands across multiple devices in parallel so I can
quickly assess the health of the entire MikroTik fleet.

**Why this priority**: Health checks are the most common day-to-day operation.
Batch execution across multiple routers dramatically reduces operational time.

**Independent Test**: Can be tested with a mock MikroTik REST API server or
recorded responses. execute_mikrotik_command_batch can be tested with multiple
device names against a mock.

**Acceptance Scenarios**:

1. **Given** multiple MikroTik routers are configured and reachable,
   **When** the operator calls `execute_mikrotik_command_batch(["router1","router2"], "/system resource print")`,
   **Then** the system executes the command on both routers in parallel and
   returns per-device results with success/failure status.

2. **Given** one router in the batch is unreachable,
   **When** the operator calls `execute_mikrotik_command_batch` with that router,
   **Then** the system returns CONNECTION_ERROR for that router while still
   processing reachable routers, and does not fail the entire batch.

3. **Given** a command matches the blocklist (e.g., `/system reboot`),
   **When** the operator attempts to execute it,
   **Then** the system returns BLOCKED_OPERATION error with explanation
   and does not send the command to the device.

4. **Given** the operator wants to check interface status on all MikroTik routers,
   **When** the operator calls `execute_mikrotik_command_batch(all_routers, "/interface print")`,
   **Then** the system returns interface status for all routers including
   name, type, status (disabled/running), and actual MTU.

---

### User Story 3 - MikroTik Configuration Retrieval (Priority: P1)

As a network engineer, I want to retrieve running configuration from MikroTik
routers via structured REST API calls so I can audit current state without
having to parse CLI output.

**Why this priority**: Configuration retrieval is read-only and safe, forming
the baseline for all subsequent change operations. The structured REST API
response is far easier to parse than CLI text.

**Independent Test**: Can be tested against mock REST API responses for
paths like /ip/address, /ip/route, /routing/bgp/session.

**Acceptance Scenarios**:

1. **Given** a MikroTik router is reachable,
   **When** the operator calls `get_mikrotik_config("router", "/ip/address")`,
   **Then** the system returns a JSON array of IP address entries with .id,
   address, interface, disabled, and dynamic fields.

2. **Given** the operator requests BGP session status,
   **When** the operator calls `get_mikrotik_config("router", "/routing/bgp/session")`,
   **Then** the system returns BGP peer entries with remote-address, instance,
   remote-as, state (established/idle), and prefix counts.

3. **Given** the operator requests firewall rules,
   **When** the operator calls `get_mikrotik_config("router", "/ip/firewall/filter")`,
   **Then** the system returns firewall filter rules with chain, action, src-address,
   dst-address, and protocol fields.

4. **Given** a REST API path that returns no data,
   **When** the operator calls `get_mikrotik_config` for that path,
   **Then** the system returns an empty array with success=True and count=0.

---

### User Story 4 - MikroTik Configuration Deployment (Priority: P2)

As a network engineer deploying configuration changes to MikroTik routers,
I want to apply changes via REST API with ITSM gate validation so all
changes are properly authorized and audited.

**Why this priority**: Configuration changes are the primary value-add of
automation. ITSM gating ensures compliance with change management processes.

**Independent Test**: Can be tested by calling load_and_commit_config with
mock data. ITSM gate can be tested with NETCLAW_LAB_MODE=true.

**Acceptance Scenarios**:

1. **Given** a ServiceNow CR in Implement state,
   **When** the operator calls `load_and_commit_config` with a valid CR number,
   **Then** the system applies the configuration change and returns success=True
   with the API response data.

2. **Given** no ServiceNow CR number is provided,
   **When** the operator attempts to apply a configuration change,
   **Then** the system returns ITSM_ERROR requiring a CR number.

3. **Given** a ServiceNow CR that is not in Implement state,
   **When** the operator attempts to apply a configuration change,
   **Then** the system returns ITSM_ERROR indicating the CR is not in the
   correct state.

4. **Given** NETCLAW_LAB_MODE=true is set,
   **When** the operator applies a configuration change without a CR,
   **Then** the system bypasses ITSM validation and applies the change,
   logging that lab mode was used.

5. **Given** a configuration change that matches the blocklist,
   **When** the operator attempts to apply it,
   **Then** the system returns BLOCKED_OPERATION error and does not
   send the change to the device.

---

### User Story 5 - MikroTik Template-Based Configuration (Priority: P2)

As a network engineer deploying consistent configuration across multiple
MikroTik routers, I want to render Jinja2 templates with YAML variables
and apply them so I can deploy standardized configurations efficiently.

**Why this priority**: Template-based deployment ensures consistency across
the fleet while allowing per-device customization via variables.

**Independent Test**: Can be tested with mock templates and YAML vars.
Dry-run mode can be verified without any actual device connection.

**Acceptance Scenarios**:

1. **Given** a valid Jinja2 template and YAML variables,
   **When** the operator calls `render_and_apply_j2_template` with dry_run=true,
   **Then** the system returns the rendered configuration without applying
   it to any device.

2. **Given** a valid template, YAML vars, and a target router,
   **When** the operator calls `render_and_apply_j2_template` with dry_run=false
   and a valid ServiceNow CR,
   **Then** the system renders the template, executes each command via
   /rest/terminal/sync, and returns per-device per-command results.

3. **Given** invalid YAML in the variables content,
   **When** the operator attempts to render a template,
   **Then** the system returns a validation error indicating the YAML parse failure.

4. **Given** a template that renders a blocklisted command,
   **When** the operator attempts to apply it (dry_run=false),
   **Then** the system returns BLOCKED_OPERATION for the specific command
   and does not apply any subsequent commands.

---

## Technical Design

### Protocol
MikroTik RouterOS REST API v7 — HTTP/HTTPS on port 8728/8729 with Basic Authentication.

### API Coverage
Based on RouterOS REST API OpenAPI spec v7.22.1 (from tikoci/restraml project).
Supports ALL REST API paths including:
- IP: /ip/address, /ip/route, /ip/firewall/*, /ip/dhcp-server, etc.
- Routing: /routing/bgp/*, /routing/ospf/*, /routing/rip, /routing/isis, etc.
- Interface: /interface/ethernet, /interface/bridge, /interface/vlan, etc.
- PPP: /ppp/secret, /ppp/profile, /ppp/active
- User: /user, /user/active, /user/ssh-keys
- System: /system/resource, /system/identity, /system/history
- Terminal: /rest/terminal/sync (CLI execution)

### MCP Tools (10)
1. get_router_list — List devices
2. add_device — Add device to inventory
3. reload_devices — Reload inventory from file
4. execute_mikrotik_command — Single device CLI exec
5. execute_mikrotik_command_batch — Multi-device parallel CLI exec
6. get_mikrotik_config — Read config via REST
7. mikrotik_config_diff — Compare against history
8. load_and_commit_config — Apply config changes (ITSM-gated)
9. render_and_apply_j2_template — Jinja2 template rendering
10. gather_device_facts — Get device info

### Safety
- Command blocklist: Prevents destructive CLI (reboot, shutdown, file ops)
- Config blocklist: Prevents dangerous REST operations
- ITSM gate: ServiceNow CR validation for config writes
- Credential filtering: Passwords never appear in output
