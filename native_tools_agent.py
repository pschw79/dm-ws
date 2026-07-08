"""Part 8 — Native tools (starter).

The Part 7 connected agent is complete below. Your tasks are:
  - TODO (step 2) Implement the native parse_label function tool (paste the provided snippet)
  - TODO (step 2) Register PARSE_LABEL_TOOL in all_tools inside run_agent
  - TODO (step 2) Dispatch parse_label calls in-process (not via the MCP server)
  - (step 3 is pre-provisioned — just run --parse-label to see your tool produce real output)

Follow the lab steps in docs/segments/08-native-tools.md.

Run:
    python starter/08-1-native-tools-agent.py --show-tools
    python starter/08-1-native-tools-agent.py --parse-label
    python starter/08-1-native-tools-agent.py --parse-label --label "???"
    python starter/08-1-native-tools-agent.py --order DM-1037 --show-steps

Compare with the completed version at baseline/08-1-native-tools-agent.py.
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
from openai import AzureOpenAI

import re
 
_ORDER_RE   = re.compile(r"\b(?:DM|PKG)-[\w-]+", re.IGNORECASE)
_ROUTE_RE   = re.compile(r"\b(?:rte|route)\s*((?:R|ROUTE)-[\w-]+)", re.IGNORECASE)
_FRAGILE_RE = re.compile(r"\b(?:fragile|frgile|frgl|frg)\b", re.IGNORECASE)


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
    """Parse a raw shipping label into structured fields (orderId, fragile, route, confidence)."""
    order_match   = _ORDER_RE.search(raw_label)
    route_match   = _ROUTE_RE.search(raw_label)
    fragile_match = _FRAGILE_RE.search(raw_label)

    if not order_match:
        return json.dumps({"error": "unparseable", "rawLabel": raw_label})

    order_id = order_match.group(0).upper()
    route    = route_match.group(1).upper() if route_match else None
    fragile  = fragile_match is not None

    confidence = 1.0
    if not route:
        confidence -= 0.15
    if fragile_match and fragile_match.group(0).lower() not in ("fragile",):
        confidence -= 0.08  # fuzzy spelling

    return json.dumps({
        "orderId":    order_id,
        "fragile":    fragile,
        "route":      route,
        "confidence": round(confidence, 2),
    })

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

                        # TODO (step 2): if tc.function.name == "parse_label", call
                        # parse_label(**args) in-process instead of going to the MCP server.
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
    print(f"  parse_label — {parse_label.__doc__.splitlines()[0]}")
    print()
    print("MCP tools (served by mcp_server.py / packagemcp):")
    for t in tools_result.tools:
        first_line = (t.description or "").splitlines()[0]
        print(f"  {t.name} — {first_line}")


def run_parse_label(label: str) -> None:
    print(f"Input : {label!r}")
    result = parse_label(label)
    parsed = json.loads(result)
    print(f"Output: {json.dumps(parsed, indent=2)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dunder Mifflin native tools agent")
    parser.add_argument("--order", help="Package/order ID to investigate")
    parser.add_argument("--show-steps", action="store_true", help="Print each tool call and result")
    parser.add_argument("--show-tools", action="store_true", help="List native and MCP tools")
    parser.add_argument("--parse-label", action="store_true",
                        help="Run parse_label on --label and print the structured output")
    parser.add_argument("--label", default="DM-1037 frgile  rte R-2",
                        help="Label text for --parse-label")
    args = parser.parse_args()

    if args.show_tools:
        asyncio.run(show_tools_async())
    elif args.parse_label:
        run_parse_label(args.label)
    elif args.order:
        asyncio.run(
            run_agent(
                f"What should I do with order {args.order}?",
                show_steps=args.show_steps,
            )
        )
    else:
        parser.print_help()
