"""Part 8 — Native tools & A2A handoff (starter).

The Part 7 connected agent is complete below. Your tasks are:
  - TODO (step 2) Implement the native parse_label function tool (paste the provided snippet)
  - TODO (step 2) Register PARSE_LABEL_TOOL in all_tools inside run_agent
  - TODO (step 2) Dispatch parse_label calls in-process (not via the MCP server)
  - (step 3 is pre-provisioned — just run --compare-tools)
  - TODO (step 4) Write the explicit handoff contract (input, artifact, failure) as a comment
  - TODO (step 5) Implement PackageLabelParser.run and RegionalManagerAgent.handle_label
  - TODO (step 6) Run --handoff --label "???" --show-handoff and verify failure behavior

Follow the lab steps in docs/segments/08-native-tools.md (steps 1-3) and docs/segments/09-a2a-handoff.md (steps 1-4).

Run:
    python starter/08-1-a2a-agent.py --show-tools
    python starter/08-1-a2a-agent.py --compare-tools
    python starter/08-1-a2a-agent.py --handoff --label "DM-1037 frgile rte R-2"
    python starter/08-1-a2a-agent.py --handoff --label "???" --show-handoff
    python starter/08-1-a2a-agent.py --order DM-1037 --show-steps

Compare with the completed version at baseline/08-1-a2a-agent.py.
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

# ── TODO (step 2): Native parse_label function tool ───────────────────────────
#
# Implement a plain Python function (no MCP server needed) that parses a raw
# shipping label string into structured fields.
#
# Contract
#   Inputs : raw_label (str) — the messy text from a physical label.
#   Returns: JSON string {orderId, fragile, route, confidence} on success.
#            JSON string {error: "unparseable", rawLabel} when no order ID found.
#   Read-only: must not write to any system.
#
# Hints
#   - Order ID pattern  : "DM-" followed by one or more digits (e.g. DM-1037)
#   - Fragile indicator : words like "fragile", "frgile", "frgl"
#   - Route pattern     : "R-" followed by a digit, possibly preceded by "rte" or "route"
#   - Confidence        : start at 1.0; penalise for missing route (-0.15) or fuzzy spelling (-0.08)

def parse_label(raw_label: str) -> str:
    """Parse a raw shipping label string into structured fields.

    TODO: implement this function following the contract above.
    """
    return json.dumps({"error": "not implemented", "rawLabel": raw_label})


# OpenAI function-tool descriptor — update the description once parse_label works.
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


# ── TODO (steps 4-6): A2A handoff ────────────────────────────────────────────
#
# Write the explicit handoff contract here before implementing the classes:
#
#   Handoff contract: RegionalManagerAgent -> PackageLabelParser
#   Input data   : rawLabel (str) — the raw shipping label text
#   Artifact     : {orderId, fragile, route, confidence} on success
#   Failure      : {error: "unparseable", rawLabel} — no system write, ever
#   Boundary     : PackageLabelParser parses only; does not reason about routes or act on systems

class PackageLabelParser:
    """Specialist agent: parses a label and returns a structured artifact.

    TODO (step 5): implement run() to call parse_label and return the parsed dict.
    """

    def run(self, raw_label: str) -> dict[str, Any]:
        # TODO: call parse_label(raw_label) and return json.loads of the result
        return {"error": "not implemented", "rawLabel": raw_label}


class RegionalManagerAgent:
    """Coordinates operational decisions; delegates label parsing to PackageLabelParser.

    TODO (step 5): implement handle_label to:
      - call self._parser.run(raw_label)
      - if show_handoff: print data sent and artifact received
      - print "RegionalManagerAgent -> PackageLabelParser -> {artifact}"
      - on error: print a hold/re-label decision
      - on success: print a route/handle action based on fragile flag
    """

    def __init__(self) -> None:
        self._parser = PackageLabelParser()

    def handle_label(self, raw_label: str, show_handoff: bool = False) -> None:
        # TODO: implement
        print("TODO: implement handle_label — see step 5")


# ── Connected agent (Part 7 complete) + native parse_label ───────────────────

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
            # TODO (step 2): replace the line below with: mcp_tools + [PARSE_LABEL_TOOL]
            all_tools = mcp_tools

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

                        # TODO (step 2): if tc.function.name == "parse_label", call
                        # parse_label(**args) in-process instead of going to the MCP server.
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
    print(f"  parse_label — {parse_label.__doc__.splitlines()[0]}")
    print()
    print("MCP tools (served by mcp_server.py / packagemcp):")
    for t in tools_result.tools:
        first_line = (t.description or "").splitlines()[0]
        print(f"  {t.name} — {first_line}")


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
    print(f"{'In-process — no server':<{col}}  {'Served by mcp_server.py':<{col}}")
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
    parser.add_argument("--compare-tools", action="store_true",
                        help="TODO (step 3): side-by-side native vs MCP comparison")
    parser.add_argument("--handoff", action="store_true",
                        help="Run RegionalManagerAgent -> PackageLabelParser handoff")
    parser.add_argument("--label", default="DM-1037 frgile  rte R-2",
                        help="Label text for --handoff")
    parser.add_argument("--show-handoff", action="store_true",
                        help="Show data sent and artifact returned")
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
