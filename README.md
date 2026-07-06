# Dunder Mifflin Workshop — Working copy

> This is the hands-on repo for the **Agentic AI Masterclass** workshop.
> You will build a series of AI agents around a fictional Dunder Mifflin
> package-manager scenario across eight parts.

## Quick start

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # fill in your Azure credentials
```

## Working directory

**Always work from this root folder** (`dm-ws/`) — not from a sub-folder. Every file you create
during the labs (`agent.py`, `mcp_server.py`, `connected_agent.py`, etc.) goes here at the
root. The `data/` folder, `.env`, and `requirements.txt` are all at the root too, so the
path resolution in the lab scripts works without any changes.

## Catching up with a baseline

Each part has a completed file in `baseline/` you can copy from if you fall behind.
Each part that needs a starting template has a file in `starter/` to begin from.

| Part | Baseline file(s) | Starter file |
|------|-----------------|--------------|
| 1 — Framing & first agent | `baseline/01-1-first-agent.py` | — |
| 2 — Context engineering | `baseline/02-1-context-map.md` | — |
| 3 — Memory | `baseline/03-1-order-memory.py`, `baseline/03-2-agent-memory.py` | — |
| 4 — Specs & personas | `baseline/04-1-spec.md` | — |
| 5 — MCP fundamentals | `baseline/05-1-mcp-design.md` | — |
| 6 — Build the MCP server | `baseline/06-1-mcp-server.py` | `starter/06-1-mcp-server.py` |
| 7 — Agent Framework & first MCP agent | `baseline/07-1-connected-agent.py` | `starter/07-1-connected-agent.py` |
| 8 — Native tools & A2A handoff | `baseline/08-1-a2a-agent.py` | `starter/08-1-a2a-agent.py` |
| 9 — Human-in-the-loop | `baseline/09-1-hitl-agent.py` | `starter/09-1-hitl-agent.py` |

Copy the baseline file to the `workshop/` root (or run it directly from `baseline/`) and
continue from there. Starter files include TODO comments marking exactly what to implement.