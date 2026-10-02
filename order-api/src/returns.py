"""Return rules. Pure functions, so the LLM never does date math."""
from dataclasses import dataclass, field
from datetime import date, timedelta

RETURN_WINDOW_DAYS = 7


@dataclass(frozen=True)
class ReturnDecision:
    eligible: bool
    reason_code: str
    return_deadline: date | None = None
    days_since_delivery: int | None = None
    non_returnable_items: list[str] = field(default_factory=list)


def decide(order: dict, today: date) -> ReturnDecision:
    status = order["status"]
    if status == "CANCELLED":
        return ReturnDecision(False, "CANCELLED")

    delivered = order.get("delivered_at")
    if status != "DELIVERED" or delivered is None:
        return ReturnDecision(False, "NOT_DELIVERED")

    deadline = delivered + timedelta(days=RETURN_WINDOW_DAYS)
    days = (today - delivered).days

    blocked = [item["name_en"] for item in order["items"] if not item["returnable"]]
    if blocked:
        return ReturnDecision(False, "NON_RETURNABLE_ITEM", deadline, days, blocked)
    if days > RETURN_WINDOW_DAYS:
        return ReturnDecision(False, "WINDOW_EXPIRED", deadline, days)
    return ReturnDecision(True, "WITHIN_WINDOW", deadline, days)
