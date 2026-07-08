"""Part 1 — First agent.

Answers questions about Dunder Mifflin orders by giving the model the full
package data as context. No tools, no retrieval — just a raw context window.

Run:
    python baseline/01-1-first-agent.py --ask "Where is order #1037?"
    python baseline/01-1-first-agent.py --ask "Which packages are on route R-2?"
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

# -- Load data ----------------------------------------------------------------
_root = Path(__file__).parent
PACKAGES = json.loads((_root / "data/packages.json").read_text())
ROUTES   = json.loads((_root / "data/routes.json").read_text())

# -- Azure OpenAI client ------------------------------------------------------
client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version="2024-05-01-preview",
)
MODEL = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.5")

SYSTEM = f"""You are the Dunder Mifflin package manager assistant.
You help warehouse staff and managers look up package status, routes, and conditions.

Current package data:
{json.dumps(PACKAGES, indent=2)}

Current route data:
{json.dumps(ROUTES, indent=2)}

Answer questions based only on the data above. If something is not in the data, say so.
"""


def ask(question: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": question},
        ],
    )
    return response.choices[0].message.content or ""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dunder Mifflin first agent")
    parser.add_argument("--ask", required=True, help="Question to ask the agent")
    args = parser.parse_args()
    print(ask(args.ask))
