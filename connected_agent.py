import argparse
import asyncio
import json
import os
from openai import AzureOpenAI
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_PARAMS = StdioServerParameters(command="python", args=["mcp_server.py"])

INSTRUCTIONS = """\
You help Darryl, a warehouse lead, decide the next operational step for an incoming package or order.
Allowed actions: look up package, order, and route details through the package manager MCP server, then propose a next step.
Boundaries: never claim you physically moved, shipped, or rerouted anything; never act on real systems; only propose.
Grounding rule: base every factual claim on a tool result. If you have not looked something up, say so rather than guessing.
Escalation: if an order is missing a route or needs a manager's decision, ask for clarification rather than guessing.\
"""

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)
MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.5")

async def run_agent(question: str, show_steps: bool = False) -> None:
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tools = [
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

            messages = [
                {"role": "system", "content": INSTRUCTIONS},
                {"role": "user", "content": question},
            ]

            step = 0
            while True:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=tools,
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
                        result = await session.call_tool(tc.function.name, args)
                        tool_text = result.content[0].text if result.content else ""
                        if show_steps:
                            print(f"   → {tool_text}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tool_text,
                        })
                else:
                    print(msg.content)
                    break

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--order", default="PKG-2024-003")
    parser.add_argument("--show-steps", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_agent(f"What should I do with order {args.order}?", show_steps=args.show_steps))

async def get_mcp_tools() -> list[dict]:
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema,
                    },
                }
                for t in result.tools
            ]
        
if __name__ == "__main__":
    tools = asyncio.run(get_mcp_tools())
    for t in tools:
        print(t["function"]["name"], "—", t["function"]["description"])