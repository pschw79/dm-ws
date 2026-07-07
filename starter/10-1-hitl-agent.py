"""Part 10 - Human-in-the-loop & condition checker (starter).

The A2A handoff from Part 9 is complete below. This workshop is about agentic behaviour,
not writing Python from scratch, so the lab doc gives you a copy-paste snippet for every
TODO below. Open the doc and paste each snippet over the matching stub, top to bottom:

    docs/segments/10-human-in-the-loop-and-condition-checker.md

  TODO (step 2) Paste fetch_package        - fetch live data via the MCP server
  TODO (step 2) Paste suggest_condition    - return one of VALID_CONDITIONS + confidence
  TODO (step 2) Paste proposed_action_for  - map condition -> action string
  TODO (step 3) Confirm VALID_CONDITIONS covers all required categories (no edit needed)
  TODO (step 4) Paste escalation_reason    - the three escalation rules
  TODO (step 5) Paste the confirmation-gate block into cmd_check_condition
  TODO (step 6) Paste build_review_payload - what the reviewer needs to decide
  TODO (step 7) Paste record_decision      - the audit artifact, then run both paths

Condition categories: OK, damaged, unclear, missing label, wrong address, needs inspection

Escalation rules to implement:
  Rule 1 - Confidence below 0.85
  Rule 2 - High-risk condition (damaged, missing label, wrong address)
  Rule 3 - Customer-impacting or irreversible proposed action

Run:
    python starter/10-1-hitl-agent.py --check-condition --order PKG-2024-009
    python starter/10-1-hitl-agent.py --check-condition --order PKG-2024-009 --propose-action
    python starter/10-1-hitl-agent.py --check-condition --order PKG-2024-004 --propose-action
    python starter/10-1-hitl-agent.py --check-condition --order PKG-2024-009 --decide approve --by Darryl
    python starter/10-1-hitl-agent.py --check-condition --order PKG-2024-006 --decide correct --to damaged --by Darryl --note "Photo shows crushed corner"

Compare with the completed version at baseline/10-1-hitl-agent.py.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
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

# ── TODO (step 3): Condition categories ───────────────────────────────────────
# Confirm these cover all required categories from the lab; add any missing ones.
VALID_CONDITIONS = frozenset({
    "OK", "damaged", "unclear", "missing label", "wrong address", "needs inspection",
})
HIGH_RISK_CONDITIONS = frozenset({"damaged", "missing label", "wrong address"})
CUSTOMER_IMPACTING_KEYWORDS = frozenset({
    "mark-damaged", "queue-customer-followup", "reroute", "hold",
})

# ── TODO (step 4): Escalation rules ───────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.85


def escalation_reason(
    condition: str,
    confidence: float,
    proposed_action: str | None,
) -> str | None:
    """Return the first escalation rule that fires, or None if safe to proceed.

    TODO: implement the three rules:
      Rule 1 - confidence < CONFIDENCE_THRESHOLD
      Rule 2 - condition in HIGH_RISK_CONDITIONS
      Rule 3 - proposed_action contains a CUSTOMER_IMPACTING_KEYWORD
    Return a descriptive string naming the rule that fired, or None.
    """
    return None  # TODO: replace with rule checks


# ── TODO (step 2): PackageConditionChecker ────────────────────────────────────

async def fetch_package(package_id: str) -> dict[str, Any] | None:
    """Fetch live package data via the running MCP server.

    TODO: open a stdio_client session to SERVER_PARAMS, call session.initialize(),
    then call session.call_tool("lookup_package", {"package_id": package_id}).
    Parse the returned text into a dict of key=value fields and return it.
    Return None if the tool returns an error string.
    """
    return None  # TODO: implement


def suggest_condition(package_data: dict[str, Any]) -> tuple[str, float]:
    """Suggest a condition and confidence score from the package fields.

    TODO: inspect package_data (status, fragile, truck, and the raw text of all values)
    and return (condition, confidence) where condition is one of VALID_CONDITIONS
    and confidence is a float between 0.0 and 1.0.

    Starting hints:
      - "missing label" in raw text   -> ("missing label", 0.95)
      - "wrong address" in raw text   -> ("wrong address", 0.90)
      - status == "damaged" (or "damag" in raw) -> ("damaged", 0.88)
      - status == "returned"          -> ("needs inspection", 0.80)
      - fragile and no truck assigned -> ("unclear",        0.72)
      - status packaged/shipped/delivered -> ("OK",         0.96)
    """
    return "unclear", 0.50  # TODO: replace with real logic


def proposed_action_for(condition: str) -> str:
    """Return the standard proposed action string for a condition category.

    TODO: return the right action for each condition:
      OK               -> "proceed-normally"
      damaged          -> "mark-damaged + queue-customer-followup"
      unclear          -> "schedule-inspection"
      missing label    -> "hold + queue-customer-followup"
      wrong address    -> "hold + queue-customer-followup"
      needs inspection -> "route-to-inspection-bay"
    """
    return "schedule-inspection"  # TODO: replace with mapping


# ── TODO (step 6): Human review payload ───────────────────────────────────────

def build_review_payload(
    package_id: str,
    package_data: dict[str, Any],
    condition: str,
    confidence: float,
    escalation_rule: str,
    action: str,
) -> dict[str, Any]:
    """Assemble the human review payload so the reviewer can decide well.

    TODO: return a dict with:
      - package_id, evidence (the raw package_data)
      - suggested condition and confidence
      - confirmed: False (not yet)
      - escalation_reason (the rule that fired)
      - proposed_action
      - options: ["approve", "reject", "correct"]
    """
    return {}  # TODO: implement


# ── TODO (step 7): Audit artifact ─────────────────────────────────────────────

def record_decision(
    package_id: str,
    original_condition: str,
    decision: str,
    corrected_to: str | None,
    by: str,
    note: str,
    action: str,
) -> dict[str, Any]:
    """Create an audit artifact capturing the human decision.

    TODO: return a dict with:
      - package_id, decision (approve/reject/correct)
      - original_condition, final_condition (corrected_to if decision=="correct")
      - corrected_to (or None)
      - decided_by, rationale (note), action (adjusted if corrected), timestamp
    """
    return {}  # TODO: implement


# ── Main command handler ───────────────────────────────────────────────────────

async def cmd_check_condition(
    order_id: str,
    propose_action: bool,
    decide: str | None,
    corrected_to: str | None,
    decided_by: str,
    note: str,
) -> None:
    package_id   = order_id
    package_data = await fetch_package(package_id)

    if package_data is None:
        print(f"Error: package {package_id} not found.")
        return

    condition, confidence = suggest_condition(package_data)
    action = proposed_action_for(condition)

    print(
        f"Order {package_id} -> suggested: {condition} "
        f"(confidence {confidence:.2f}), not confirmed"
    )

    # ── TODO (step 5): paste the confirmation-gate block here ────────────────
    # Replace this comment with the step 5 snippet from the lab doc. It computes
    # `esc = escalation_reason(...)`, then:
    #   - pauses and prints the review payload when a rule fires (--propose-action)
    #   - prints "safe to proceed" when no rule fires
    #   - records and prints the audit artifact when --decide is set (step 7)


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
