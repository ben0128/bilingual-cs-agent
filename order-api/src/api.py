"""FastAPI app: two webhook-tool endpoints for the voice agent.

Business errors return 200 with ok=false so the agent can keep talking;
only auth or server problems return 4xx/5xx.
"""
from datetime import date

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

import repository
import returns
from auth import require_tool_secret
from normalize import normalize_order_id, normalize_phone_last4

# /docs and /openapi.json are routed to the Worker in wrangler.jsonc; /redoc is not, so it is off.
app = FastAPI(title="Nova Mart order API", version="0.1.0", redoc_url=None)


class OrderLookup(BaseModel):
    order_id: str = Field(description="Order ID as heard; normalized server-side")
    phone_last4: str = Field(description="Last 4 digits of the phone on the order")


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


def _error(code: str) -> dict:
    print(f"tool_error code={code}")  # never log the phone digits
    return {"ok": False, "error_code": code}


def _lookup(body: OrderLookup, today: date) -> tuple[dict | None, dict | None]:
    order_id = normalize_order_id(body.order_id)
    if order_id is None:
        return None, _error("INVALID_ORDER_ID")
    phone = normalize_phone_last4(body.phone_last4)
    order = repository.find_order(order_id, phone, today) if phone else None
    if order is None:
        print(f"lookup_miss order_id={order_id}")
        return None, _error("ORDER_NOT_FOUND")
    return order, None


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/tools/order-status", dependencies=[Depends(require_tool_secret)])
async def order_status(body: OrderLookup):
    today = repository.today_taipei()
    order, err = _lookup(body, today)
    if err:
        return err
    return {
        "ok": True,
        "order_id": order["order_id"],
        "status": order["status"],
        "carrier": order["carrier"],
        "ordered_at": _iso(order["ordered_at"]),
        "shipped_at": _iso(order["shipped_at"]),
        "delivered_at": _iso(order["delivered_at"]),
        "eta": _iso(order["eta"]),
        "items": [
            {"name_zh": i["name_zh"], "name_en": i["name_en"], "qty": i["qty"]}
            for i in order["items"]
        ],
    }


@app.post("/tools/return-eligibility", dependencies=[Depends(require_tool_secret)])
async def return_eligibility(body: OrderLookup):
    today = repository.today_taipei()
    order, err = _lookup(body, today)
    if err:
        return err
    decision = returns.decide(order, today)
    return {
        "ok": True,
        "order_id": order["order_id"],
        "eligible": decision.eligible,
        "reason_code": decision.reason_code,
        "delivered_at": _iso(order["delivered_at"]),
        "return_deadline": _iso(decision.return_deadline),
        "days_since_delivery": decision.days_since_delivery,
        "non_returnable_items": decision.non_returnable_items,
    }
