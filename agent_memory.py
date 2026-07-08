from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI
from order_memory import extract_and_store, get_context

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


def ask(question: str, session_id: str = "") -> str:
    # On the way in: extract any order reference from the user's message
    extract_and_store(session_id, question)

    memory_ctx = get_context(session_id)
    active_order = memory_ctx.get("active_order_id")
    context_hint = (
        f"\n[Memory] Active order this session: {active_order}" if active_order else ""
    )

    if context_hint:
        print(f"  {context_hint.strip()}")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": question + context_hint},
        ],
    )
    return response.choices[0].message.content or ""


if __name__ == "__main__":
    session_id = str(uuid.uuid4())
    print("Dunder Mifflin package agent — type 'quit' to exit.\n")
    while True:
        question = input("You: ").strip()
        if question.lower() in ("quit", "exit", "q"):
            break
        print(f"Agent: {ask(question, session_id)}\n")