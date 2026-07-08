"""Part 6 — Build the MCP server.

Exposes the Dunder Mifflin package manager capabilities over MCP:
  Resources : resource://package-status-policy
  Prompts   : investigate_delayed_package
  Tools     : list_packages, lookup_package, lookup_order_status, lookup_route

Validate standalone with:
    mcp dev baseline/06-1-mcp-server.py        # open MCP Inspector in the browser
    python baseline/06-1-mcp-server.py         # verify it starts without errors (Ctrl+C to stop)
"""
import os

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

_BASE_URL = os.getenv("PACKAGE_API_URL", "http://localhost:8000")
_PERSONA  = os.getenv("PACKAGE_API_PERSONA", "jim-halpert")

# The name is shown when a client or agent inspects this server.
mcp = FastMCP("package-manager")


def _get(path: str) -> dict | list | None:
    """GET from the package-this API. Returns None on 404."""
    r = httpx.get(
        f"{_BASE_URL}{path}",
        headers={"X-Persona-Id": _PERSONA},
        timeout=10.0,
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


# --- Tools (callable functions the agent can invoke) -------------------------

@mcp.tool()
def list_packages() -> str:
    """Return all package IDs in the system. Use this to discover valid IDs before calling lookup_package or lookup_order_status."""
    data = _get("/packages")
    if data is None:
        return "Error: could not retrieve package list."
    items = data.get("items", []) if isinstance(data, dict) else data
    ids = [p["package_id"] for p in items]
    return ("Packages: " + ", ".join(ids)) if ids else "No packages found."


@mcp.tool()
def lookup_package(package_id: str) -> str:
    """Look up a package by its ID (e.g. DM-1037).
    Returns status, destination, fragile flag, priority, and any delay information."""
    data = _get(f"/packages/{package_id}")
    if data is None:
        return f"Error: no package found with ID '{package_id}'."
    delay = f", delay_reason={data['delay_reason']}" if data.get("delay_reason") else ""
    return (
        f"Package {package_id}: status={data['status']}, "
        f"destination={data.get('destination')}, fragile={data.get('fragile')}, "
        f"priority={data.get('priority')}, truck={data.get('truck_id') or 'none'}"
        f"{delay}"
    )


@mcp.tool()
def lookup_order_status(package_id: str) -> str:
    """Return the current delivery status and delay details for a package (e.g. DM-1037). Read-only."""
    data = _get(f"/packages/{package_id}")
    if data is None:
        return f"Error: no package found with ID '{package_id}'."
    parts = [f"status={data['status']}"]
    if data.get("delay_reason"):
        parts.append(f"delay_reason={data['delay_reason']}")
    if data.get("delay_duration_hours") is not None:
        parts.append(f"delay_hours={data['delay_duration_hours']}")
    if data.get("expected_delivery"):
        parts.append(f"expected_delivery={data['expected_delivery']}")
    return f"Order status for {package_id}: " + ", ".join(parts)


@mcp.tool()
def lookup_route(route_id: str) -> str:
    """Return route and driver information for a given route ID (e.g. R-2). Read-only."""
    data = _get(f"/routes/{route_id}")
    if data is None:
        return f"Error: no route found with ID '{route_id}'."
    return str(data)


# --- Prompt (a reusable instruction template) --------------------------------

@mcp.prompt()
def investigate_delayed_package(orderId: str) -> str:
    """Reusable workflow for investigating a delayed or problematic package."""
    return f"""\
Investigate the package for order {orderId}. Follow these steps:

1. Call list_packages() to find the package ID matching order {orderId}.
2. Call lookup_package(<packageId>) to get the full record.
3. Call lookup_order_status(<packageId>) for delivery progress and any delay details.
4. If a route is returned, call lookup_route(<routeId>) to see all packages on that route.
5. Check the status against the policy (resource://package-status-policy).
6. Summarise findings and propose one concrete next step for Darryl.

Ground every claim in a tool result. If you have not looked something up, say so.
"""


# --- Resource (read-only reference data) -------------------------------------

@mcp.resource("resource://package-status-policy")
def package_status_policy() -> str:
    """The Dunder Mifflin package handling and status policy."""
    from pathlib import Path
    policy_path = Path(__file__).parent / "data" / "policy.md"
    if policy_path.exists():
        return policy_path.read_text()
    return "Package status policy: see Dunder Mifflin shipping guidelines."


if __name__ == "__main__":
    mcp.run()
