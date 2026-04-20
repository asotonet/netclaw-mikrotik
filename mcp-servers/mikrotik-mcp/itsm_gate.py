"""
MikroTik MCP Server - ITSM Gate (ServiceNow Change Request Validation)
Follows the same pattern as gNMI MCP itsm_gate.py
"""

from __future__ import annotations

import os
import re

from .models import ItsmsGateResult


# =============================================================================
# ITSM Gate Configuration
# =============================================================================

# Environment variable for lab mode (bypasses ServiceNow)
NETCLAW_LAB_MODE = os.environ.get("NETCLAW_LAB_MODE", "false").lower() in ("true", "1", "yes")

# CR number format: CHG followed by digits
CR_NUMBER_PATTERN = re.compile(r"^CHG\d+$")


def validate_change_request(cr_number: str) -> ItsmsGateResult:
    """
    Validate that a ServiceNow Change Request is approved and in Implement state.

    In production: calls ServiceNow API to verify CR state.
    In lab mode (NETCLAW_LAB_MODE=true): skips validation, always returns valid.

    Args:
        cr_number: ServiceNow CR number (e.g., "CHG0012345")

    Returns:
        ItsmsGateResult with valid=True/False and state information

    Raises:
        ValueError: If CR number format is invalid
    """
    if not cr_number:
        return ItsmsGateResult(
            valid=False,
            cr_number="",
            message="Change Request number is required for configuration changes",
            bypassed=False,
        )

    # Validate CR number format
    if not CR_NUMBER_PATTERN.match(cr_number):
        return ItsmsGateResult(
            valid=False,
            cr_number=cr_number,
            message=f"Invalid CR number format: '{cr_number}'. Expected format: CHG0012345",
            bypassed=False,
        )

    # Lab mode bypass
    if NETCLAW_LAB_MODE:
        return ItsmsGateResult(
            valid=True,
            cr_number=cr_number,
            state="Lab Mode (bypassed)",
            message="NETCLAW_LAB_MODE enabled — ServiceNow validation skipped",
            bypassed=True,
        )

    # Production: Call ServiceNow API
    # Note: This requires the servicenow-mcp to be configured
    # For now, we do a simple check via environment variables if available
    servicenow_url = os.environ.get("SERVICENOW_INSTANCE_URL")
    servicenow_api_key = os.environ.get("SERVICENOW_API_KEY")

    if servicenow_url and servicenow_api_key:
        return _validate_via_servicenow_api(servicenow_url, servicenow_api_key, cr_number)
    else:
        # No ServiceNow configured — fail closed (require CR) unless in lab mode
        return ItsmsGateResult(
            valid=False,
            cr_number=cr_number,
            message="ServiceNow not configured. Set SERVICENOW_INSTANCE_URL and SERVICENOW_API_KEY or enable NETCLAW_LAB_MODE",
            bypassed=False,
        )


def _validate_via_servicenow_api(instance_url: str, api_key: str, cr_number: str) -> ItsmsGateResult:
    """Call ServiceNow API to validate Change Request state."""
    import requests

    try:
        url = f"{instance_url}/api/now/table/change_request"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        params = {"sysparm_query": f"number={cr_number}", "sysparm_fields": "number,state"}

        resp = requests.get(url, headers=headers, params=params, timeout=10)

        if resp.status_code == 200:
            records = resp.json().get("result", [])
            if not records:
                return ItsmsGateResult(
                    valid=False,
                    cr_number=cr_number,
                    message=f"Change Request '{cr_number}' not found in ServiceNow",
                    bypassed=False,
                )

            record = records[0]
            state = record.get("state", "0")

            # State 4 = Implement (approved for work)
            # State -1 = Canceled, 1 = New, 2 = Assess, 3 = Authorized
            implement_states = ["4"]
            if state in implement_states:
                return ItsmsGateResult(
                    valid=True,
                    cr_number=cr_number,
                    state=f"Implement ({state})",
                    message=f"Change Request '{cr_number}' is approved and in Implement state",
                    bypassed=False,
                )
            else:
                return ItsmsGateResult(
                    valid=False,
                    cr_number=cr_number,
                    state=f"State {state}",
                    message=f"Change Request '{cr_number}' is not in Implement state (current state: {state})",
                    bypassed=False,
                )
        else:
            return ItsmsGateResult(
                valid=False,
                cr_number=cr_number,
                message=f"ServiceNow API error: HTTP {resp.status_code}",
                bypassed=False,
            )

    except Exception as e:
        return ItsmsGateResult(
            valid=False,
            cr_number=cr_number,
            message=f"ServiceNow API call failed: {str(e)}",
            bypassed=False,
        )
