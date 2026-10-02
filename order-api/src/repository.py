"""Read-only order lookup.

Workers isolates can be recycled at any time, so nothing here keeps mutable
state: real dates are computed from the seed offsets on every request.
"""
from datetime import date, datetime, timedelta, timezone

from seed import DEMO_PHONE_LAST4, ORDERS

TAIPEI = timezone(timedelta(hours=8))
_BY_ID = {o["order_id"]: o for o in ORDERS}


def today_taipei() -> date:
    return datetime.now(TAIPEI).date()


def _ago(today: date, days: int | None) -> date | None:
    return None if days is None else today - timedelta(days=days)


def find_order(order_id: str, phone_last4: str, today: date) -> dict | None:
    """Return the order with real dates, or None.

    A wrong phone number returns None exactly like an unknown order, so a
    caller cannot probe which order IDs exist.
    """
    raw = _BY_ID.get(order_id)
    if raw is None or phone_last4 != DEMO_PHONE_LAST4:
        return None
    eta = raw.get("eta_in_days")
    return {
        "order_id": raw["order_id"],
        "status": raw["status"],
        "carrier": raw["carrier"],
        "ordered_at": _ago(today, raw.get("ordered_days_ago")),
        "shipped_at": _ago(today, raw.get("shipped_days_ago")),
        "delivered_at": _ago(today, raw.get("delivered_days_ago")),
        "eta": None if eta is None else today + timedelta(days=eta),
        "items": raw["items"],
    }
