"""Part 10 - Human-in-the-loop & condition checker.

Extends Part 8 with a PackageConditionChecker that:
  - Fetches live package data via the running MCP server
  - Suggests a condition with a confidence score
  - Escalates based on risk-based rules (confidence, risk, policy, irreversibility)
  - Pauses for human confirmation before customer-impacting or irreversible actions
  - Records the human decision and rationale as an audit artifact

Condition categories: OK, damaged, unclear, missing label, wrong address, needs inspection

Escalation rules:
  Rule 1 - Confidence below threshold (< 0.85)
  Rule 2 - High-risk condition: damaged, missing label, or wrong address
  Rule 3 - Customer-impacting or irreversible proposed action

Run:
    python baseline/10-1-hitl-agent.py --check-condition --order PKG-2024-009
    python baseline/10-1-hitl-agent.py --check-condition --order PKG-2024-009 --propose-action
    python baseline/10-1-hitl-agent.py --check-condition --order PKG-2024-004 --propose-action
    python baseline/10-1-hitl-agent.py --check-condition --order PKG-2024-009 --decide approve --by Darryl
    python baseline/10-1-hitl-agent.py --check-condition --order PKG-2024-006 --decide correct --to damaged --by Darryl --note "Photo shows crushed corner"
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

# -- MCP server ---------------------------------------------------------------
_ROOT = Path(__file__).parent
_SERVER_FILE = _ROOT / "mcp_server.py"

if _SERVER_FILE.exists():
    SERVER_PARAMS = StdioServerParameters(
        command=sys.executable,
        args=[str(_SERVER_FILE)],
    )
else:
    SERVER_PARAMS = StdioServerParameters(
        command=sys.executable,
        args=["-m", "packagemcp"],
        env={**os.environ, "PYTHONPATH": str(_ROOT)},
    )

# ── Condition categories ──────────────────────────────────────────────────────

VALID_CONDITIONS = frozenset({
    "OK", "damaged", "unclear", "missing label", "wrong address", "needs inspection",
})
HIGH_RISK_CONDITIONS = frozenset({"damaged", "missing label", "wrong address"})
CUSTOMER_IMPACTING_KEYWORDS = frozenset({
    "mark-damaged", "queue-customer-followup", "reroute", "hold",
})

# ── Escalation rules ──────────────────────────────────────────────────────────

CONFIDENCE_THRESHOLD = 0.85


def escalation_reason(
    condition: str,
    confidence: float,
    proposed_action: str | None,
) -> str | None:
    """Return the first escalation rule that fires, or None if safe to proceed."""
    if confidence < CONFIDENCE_THRESHOLD:
        return (
            f"Rule 1: confidence {confidence:.2f} is below threshold "
            f"{CONFIDENCE_THRESHOLD} - human confirmation required"
        )
    if condition in HIGH_RISK_CONDITIONS:
        return (
            f"Rule 2: condition '{condition}' is high-risk - "
            "human review required before any downstream action"
        )
    if proposed_action and any(kw in proposed_action for kw in CUSTOMER_IMPACTING_KEYWORDS):
        return (
            f"Rule 3: proposed action '{proposed_action}' is customer-impacting or "
            "irreversible - human confirmation required"
        )
    return None


# ── PackageConditionChecker ───────────────────────────────────────────────────

async def fetch_package(package_id: str) -> dict[str, Any] | None:
    """Fetch live package data via the running MCP server."""
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("lookup_package", {"package_id": package_id})
            text = result.content[0].text if result.content else ""
            if text.startswith("Error:"):
                return None
            # Parse "key=value, key=value" text into a dict
            fields: dict[str, Any] = {}
            # Strip the "Package PKG-XXXX: " prefix if present
            if ": " in text:
                text = text.split(": ", 1)[1]
            for part in text.split(", "):
                if "=" in part:
                    k, v = part.split("=", 1)
                    fields[k.strip()] = v.strip()
            return fields


def suggest_condition(package_data: dict[str, Any]) -> tuple[str, float]:
    """Suggest a condition and confidence from available package fields.

    Returns (condition, confidence) where condition is one of VALID_CONDITIONS.
    """
    raw = " ".join(str(v) for v in package_data.values()).lower()
    status  = package_data.get("status", "").lower()
    fragile = str(package_data.get("fragile", "false")).lower() == "true"
    truck   = str(package_data.get("truck", package_data.get("truck_id", ""))).strip().lower()

    if "missing label" in raw or "missing_label" in raw:
        return "missing label", 0.95
    if "wrong address" in raw or "wrong_address" in raw:
        return "wrong address", 0.90
    if status == "damaged" or "damag" in raw:
        return "damaged", 0.88
    if status == "returned":
        return "needs inspection", 0.80
    if fragile and truck in ("none", ""):
        return "unclear", 0.72  # fragile with no truck assigned: ambiguous
    if status in ("order_created", "packaged", "ready_for_shipping", "shipped", "delivered"):
        return "OK", 0.96
    return "unclear", 0.60


def proposed_action_for(condition: str) -> str:
    """Return the standard proposed action for a condition category."""
    return {
        "OK":               "proceed-normally",
        "damaged":          "mark-damaged + queue-customer-followup",
        "unclear":          "schedule-inspection",
        "missing label":    "hold + queue-customer-followup",
        "wrong address":    "hold + queue-customer-followup",
        "needs inspection": "route-to-inspection-bay",
    }.get(condition, "schedule-inspection")


# ── Human review payload ──────────────────────────────────────────────────────

def build_review_payload(
    package_id: str,
    package_data: dict[str, Any],
    condition: str,
    confidence: float,
    escalation_rule: str,
    action: str,
) -> dict[str, Any]:
    """Assemble the human review payload so the reviewer can decide well."""
    return {
        "package_id":        package_id,
        "evidence":          package_data,
        "suggested":         condition,
        "confidence":        confidence,
        "confirmed":         False,
        "escalation_reason": escalation_rule,
        "proposed_action":   action,
        "options":           ["approve", "reject", "correct"],
    }


# ── Audit artifact ────────────────────────────────────────────────────────────

def record_decision(
    package_id: str,
    original_condition: str,
    decision: str,
    corrected_to: str | None,
    by: str,
    note: str,
    action: str,
) -> dict[str, Any]:
    """Create an audit artifact capturing the human decision."""
    final_condition = (
        corrected_to if (decision == "correct" and corrected_to) else original_condition
    )
    final_action = (
        proposed_action_for(final_condition) if decision == "correct"
        else (action if decision == "approve" else "no-action")
    )
    return {
        "package_id":         package_id,
        "decision":           decision,
        "original_condition": original_condition,
        "final_condition":    final_condition,
        "corrected_to":       corrected_to,
        "decided_by":         by,
        "rationale":          note,
        "action":             final_action,
        "timestamp":          datetime.now(timezone.utc).isoformat(),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

async def cmd_check_condition(
    order_id: str,
    propose_action: bool,
    decide: str | None,
    corrected_to: str | None,
    decided_by: str,
    note: str,
) -> None:
    package_id = order_id if order_id.upper().startswith("PKG-") else f"PKG-2024-{int(order_id):03d}"
    package_data = await fetch_package(package_id)

    if package_data is None:
        print(f"Error: package {package_id} not found.")
        return

    condition, confidence = suggest_condition(package_data)
    action = proposed_action_for(condition)
    esc = escalation_reason(condition, confidence, action if propose_action else None)

    print(
        f"Order {package_id} -> suggested: {condition} "
        f"(confidence {confidence:.2f}), not confirmed"
    )

    if not propose_action and not decide:
        return

    if propose_action and not decide:
        if esc:
            print(
                f"\nAwaiting human confirmation: proposed: {action}. "
                "No change made yet."
            )
            print(f"Escalation reason: {esc}")
            payload = build_review_payload(
                package_id, package_data, condition, confidence, esc, action
            )
            print("\nHuman review payload:")
            print(json.dumps(payload, indent=2))
        else:
            print(f"\nNo escalation required. Safe to proceed with: {action}")
        return

    if decide:
        audit = record_decision(
            package_id=package_id,
            original_condition=condition,
            decision=decide,
            corrected_to=corrected_to,
            by=decided_by,
            note=note,
            action=action,
        )
        print("\nAudit artifact:")
        print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dunder Mifflin HITL condition checker")
    parser.add_argument("--check-condition", action="store_true",
                        help="Run the condition checker for an order")
    parser.add_argument("--order", help="Package/order ID (e.g. PKG-2024-009)")
    parser.add_argument("--propose-action", action="store_true",
                        help="Show proposed action and human confirmation gate")
    parser.add_argument("--decide", choices=["approve", "reject", "correct"],
                        help="Record a human decision")
    parser.add_argument("--to", dest="corrected_to",
                        help="Corrected condition (required with --decide correct)")
    parser.add_argument("--by", dest="decided_by", default="Darryl",
                        help="Name of the human making the decision")
    parser.add_argument("--note", default="", help="Rationale for the decision")
    args = parser.parse_args()

    if args.check_condition:
        if not args.order:
            parser.error("--check-condition requires --order")
        asyncio.run(cmd_check_condition(
            order_id=args.order,
            propose_action=args.propose_action,
            decide=args.decide,
            corrected_to=args.corrected_to,
            decided_by=args.decided_by,
            note=args.note,
        ))
    else:
        parser.print_help()
