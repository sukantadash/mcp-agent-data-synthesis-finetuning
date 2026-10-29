"""Minimal FastMCP server for Agent & MCP data synthesis demos.

Start:
    uv run python mcp_server.py
    # or: python mcp_server.py

Exposes Streamable HTTP on http://127.0.0.1:8008/mcp
"""

from __future__ import annotations

from typing import Annotated, Optional
import os

from fastmcp import FastMCP

mcp = FastMCP(
    name="Order Ops",
    instructions=(
        "Order and inventory tools for an integration runtime. "
        "Use these to look up orders, check stock, and create shipments."
    ),
)

ORDERS = {
    "ORD-1001": {
        "id": "ORD-1001",
        "customer": "Acme Retail",
        "sku": "SKU-LAP-14",
        "qty": 2,
        "status": "paid",
        "ship_to": "Austin, TX",
    },
    "ORD-1002": {
        "id": "ORD-1002",
        "customer": "Northwind",
        "sku": "SKU-MON-27",
        "qty": 5,
        "status": "paid",
        "ship_to": "Seattle, WA",
    },
    "ORD-1003": {
        "id": "ORD-1003",
        "customer": "Contoso",
        "sku": "SKU-KB-MECH",
        "qty": 10,
        "status": "pending",
        "ship_to": "Boston, MA",
    },
}

INVENTORY = {
    "SKU-LAP-14": {"sku": "SKU-LAP-14", "name": "14in Ultrabook", "on_hand": 12, "warehouse": "DFW"},
    "SKU-MON-27": {"sku": "SKU-MON-27", "name": "27in Monitor", "on_hand": 3, "warehouse": "SEA"},
    "SKU-KB-MECH": {"sku": "SKU-KB-MECH", "name": "Mechanical Keyboard", "on_hand": 40, "warehouse": "BOS"},
}

SHIPMENTS: list[dict] = []


@mcp.tool()
def list_orders(
    status: Annotated[Optional[str], "Filter by status: paid | pending | shipped"] = None,
) -> list[dict]:
    """List orders, optionally filtered by status."""
    orders = list(ORDERS.values())
    if status:
        orders = [o for o in orders if o["status"] == status]
    return orders


@mcp.tool()
def get_order(
    order_id: Annotated[str, "Order ID, e.g. ORD-1001"],
) -> dict:
    """Fetch a single order by ID."""
    order = ORDERS.get(order_id)
    if not order:
        return {"error": f"Order not found: {order_id}"}
    return order


@mcp.tool()
def check_inventory(
    sku: Annotated[str, "Product SKU, e.g. SKU-LAP-14"],
) -> dict:
    """Check on-hand inventory for a SKU."""
    item = INVENTORY.get(sku)
    if not item:
        return {"error": f"SKU not found: {sku}"}
    return item


@mcp.tool()
def create_shipment(
    order_id: Annotated[str, "Order ID to ship"],
    carrier: Annotated[str, "Carrier name, e.g. UPS or FedEx"] = "UPS",
) -> dict:
    """Create a shipment for a paid order if inventory is available."""
    order = ORDERS.get(order_id)
    if not order:
        return {"error": f"Order not found: {order_id}"}
    if order["status"] != "paid":
        return {"error": f"Order {order_id} is {order['status']}; only paid orders can ship"}

    inv = INVENTORY.get(order["sku"])
    if not inv or inv["on_hand"] < order["qty"]:
        return {"error": f"Insufficient inventory for {order['sku']}"}

    inv["on_hand"] -= order["qty"]
    order["status"] = "shipped"
    shipment = {
        "shipment_id": f"SHP-{len(SHIPMENTS) + 1:04d}",
        "order_id": order_id,
        "carrier": carrier,
        "sku": order["sku"],
        "qty": order["qty"],
        "warehouse": inv["warehouse"],
    }
    SHIPMENTS.append(shipment)
    return shipment


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8008"))
    # Streamable HTTP endpoint for MCPAgentBlock / Langflow
    mcp.run(transport="http", host="127.0.0.1", port=port)
