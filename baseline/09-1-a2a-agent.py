"""Part 9 - A2A handoff.

Extends the Part 8 native-tools agent with:
  - An explicit RegionalManagerAgent -> PackageLabelParser A2A handoff

Uses the live mcp_server.py for MCP tools; falls back to packagemcp.

Run:
    python baseline/09-1-a2a-agent.py --show-tools
    python baseline/09-1-a2a-agent.py --compare-tools
    python baseline/09-1-a2a-agent.py --handoff --label "DM-1037 frgile rte R-2"
    python baseline/09-1-a2a-agent.py --handoff --label "???" --show-handoff
    python baseline/09-1-a2a-agent.py --order DM-1037 --show-steps
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AzureOpenAI

load_dotenv()

# -- MCP server ---------------------------------------------------------------
_ROOT = Path(__file__).parent.parent  # workshop/
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

# -- Azure OpenAI client ------------------------------------------------------
client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version="2024-05-01-preview",
)
MODEL = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.5")

INSTRUCTIONS = """\
You help Darryl, a warehouse lead, decide the next operational step for an incoming package or order.
Allowed actions: look up package, order, and route details through the package manager MCP server,
              and call parse_label to extract structured fields from a raw shipping label.
Boundaries: never claim you physically moved, shipped, or rerouted anything; never act on real systems; only propose.
Grounding rule: base every factual claim on a tool result. If you have not looked something up, say so rather than guessing.
Escalation: if an order is missing a route or needs a manager's decision, ask for clarification rather than guessing.\
"""

# ── Native function tool ──────────────────────────────────────────────────────
# Runs in-process; no MCP server needed. Compare with the MCP tools below.

_ORDER_RE   = re.compile(r"\bDM-\d+\b", re.IGNORECASE)
_ROUTE_RE   = re.compile(r"\b(?:rte|route)\s*(R-\d+)\b", re.IGNORECASE)
_FRAGILE_RE = re.compile(r"\b(?:fragile|frgile|frgl|frg)\b", re.IGNORECASE)


def parse_label(raw_label: str) -> str:
    """Parse a raw shipping label string into structured fields.

    Inputs : raw_label (str) - the messy label text from the package.
    Returns: JSON {orderId, fragile, route, confidence} on success,
             or     {error, rawLabel} when no order ID is found.
    Read-only: does not write to any system.
    """
    order_match  = _ORDER_RE.search(raw_label)
    route_match  = _ROUTE_RE.search(raw_label)
    fragile_match = _FRAGILE_RE.search(raw_label)

    if not order_match:
        return json.dumps({"error": "unparseable", "rawLabel": raw_label})

    order_id = order_match.group(0).upper()
    route    = route_match.group(1).upper() if route_match else None
    fragile  = fragile_match is not None

    # Confidence: penalise for missing fields or fuzzy spellings
    confidence = 1.0
    if not route:
        confidence -= 0.15
    if fragile_match and fragile_match.group(0).lower() not in ("fragile",):
        confidence -= 0.08  # fuzzy spelling detected

    return json.dumps({
        "orderId":    order_id,
        "fragile":    fragile,
        "route":      route,
        "confidence": round(confidence, 2),
    })


# OpenAI function-tool descriptor for parse_label
PARSE_LABEL_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "parse_label",
        "description": (
            "Parse a raw shipping label string into structured fields "
            "(orderId, fragile, route, confidence). Read-only."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "raw_label": {
                    "type": "string",
                    "description": "The raw, possibly messy text from the shipping label.",
                }
            },
            "required": ["raw_label"],
        },
    },
}


# ── PackageLabelParser - A2A specialist agent ─────────────────────────────────
#
# Handoff contract
#   Input data : rawLabel (str) - the raw shipping label text.
#   Artifact   : {orderId, fragile, route, confidence} on success.
#   Failure    : {error: "unparseable", rawLabel} - no system write, ever.
#   Boundary   : parses only; does not reason about routes or act on systems.

class PackageLabelParser:
    """Specialist agent: parses a label and returns a structured artifact."""

    def run(self, raw_label: str) -> dict[str, Any]:
        return json.loads(parse_label(raw_label))


# ── RegionalManagerAgent - delegates to PackageLabelParser via handoff ────────

class RegionalManagerAgent:
    """Coordinates operational decisions; delegates label parsing to PackageLabelParser."""

    def __init__(self) -> None:
        self._parser = PackageLabelParser()

    def handle_label(self, raw_label: str, show_handoff: bool = False) -> None:
        if show_handoff:
            print("RegionalManagerAgent -> PackageLabelParser")
            print(f"  Sending : rawLabel={raw_label!r}")

        artifact = self._parser.run(raw_label)

        if show_handoff:
            print(f"  Received: {json.dumps(artifact)}")

        print(f"RegionalManagerAgent -> PackageLabelParser -> {json.dumps(artifact)}")

        if "error" in artifact:
            print("Decision: label unparseable - hold package; request re-labelling.")
        else:
            action = (
                "handle with care; verify fragile label before loading"
                if artifact["fragile"]
                else "route normally"
            )
            route = artifact.get("route") or "unknown route"
            print(f"Decision: {action} for {artifact['orderId']} on {route}.")


# ── Connected agent (Part 7) + native parse_label ────────────────────────────

async def run_agent(question: str, show_steps: bool = False) -> None:
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            mcp_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema,
                    },
                }
                for t in tools_result.tools
            ]
            all_tools = mcp_tools + [PARSE_LABEL_TOOL]

            messages = [
                {"role": "system", "content": INSTRUCTIONS},
                {"role": "user", "content": question},
            ]

            step = 0
            while True:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=all_tools,
                    tool_choice="auto",
                )
                msg = response.choices[0].message
                messages.append(msg)

                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        step += 1
                        args = json.loads(tc.function.arguments)
                        if show_steps:
                            print(f"{step}) calling {tc.function.name}({args})")

                        # Dispatch native tool in-process; MCP tools go to the server.
                        if tc.function.name == "parse_label":
                            tool_text = parse_label(**args)
                        else:
                            result = await session.call_tool(tc.function.name, args)
                            tool_text = result.content[0].text if result.content else ""

                        if show_steps:
                            print(f"   -> {tool_text}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tool_text,
                        })
                else:
                    print(msg.content)
                    break


async def show_tools_async() -> None:
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
    print("Native tools (in-process, no server):")
    print(f"  parse_label - {parse_label.__doc__.splitlines()[0]}")
    print()
    print("MCP tools (served by mcp_server.py / packagemcp):")
    for t in tools_result.tools:
        first_line = (t.description or "").splitlines()[0]
        print(f"  {t.name} - {first_line}")


async def compare_tools_async() -> None:
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
    mcp_example = next(
        (t for t in tools_result.tools if t.name == "lookup_order_status"), None
    )
    mcp_desc = mcp_example.description.splitlines()[0] if mcp_example else "lookup_order_status"

    col = 44
    print(f"{'Native: parse_label':<{col}}  {'MCP: lookup_order_status':<{col}}")
    print(f"{'-' * col}  {'-' * col}")
    print(f"{'In-process - no server':<{col}}  {'Served by mcp_server.py':<{col}}")
    print(f"{'Owned by this one agent':<{col}}  {'Shared by any agent':<{col}}")
    print(f"{'No deployment overhead':<{col}}  {'Independent deployment':<{col}}")
    print(f"{'Best for: small, local, single-agent job':<{col}}  {'Best for: shared, reused, evolving capability':<{col}}")
    print()
    print("Prefer native  : small, self-contained, used by exactly one agent.")
    print("Prefer MCP     : shared across agents, deployed or evolved on its own.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dunder Mifflin A2A agent")
    parser.add_argument("--order", help="Package/order ID to investigate")
    parser.add_argument("--show-steps", action="store_true", help="Print each tool call and result")
    parser.add_argument("--show-tools", action="store_true", help="List native and MCP tools")
    parser.add_argument("--compare-tools", action="store_true", help="Side-by-side native vs MCP comparison")
    parser.add_argument("--handoff", action="store_true", help="Run RegionalManagerAgent -> PackageLabelParser handoff")
    parser.add_argument("--label", default="DM-1037 frgile  rte R-2", help="Label text for --handoff")
    parser.add_argument("--show-handoff", action="store_true", help="Show data sent and artifact returned")
    args = parser.parse_args()

    if args.show_tools:
        asyncio.run(show_tools_async())
    elif args.compare_tools:
        asyncio.run(compare_tools_async())
    elif args.handoff:
        agent = RegionalManagerAgent()
        agent.handle_label(args.label, show_handoff=args.show_handoff)
    elif args.order:
        asyncio.run(
            run_agent(
                f"What should I do with order {args.order}?",
                show_steps=args.show_steps,
            )
        )
    else:
        parser.print_help()
