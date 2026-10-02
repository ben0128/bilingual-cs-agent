"""Demo orders.

Dates are stored as day offsets from today (Taipei time), so the demo behaves
the same on whichever day it runs. All orders belong to one demo customer whose
phone ends in 0912.
"""

DEMO_PHONE_LAST4 = "0912"

ORDERS = [
    {
        "order_id": "58210473",
        "status": "SHIPPED",
        "carrier": "BLACK_CAT",
        "ordered_days_ago": 3,
        "shipped_days_ago": 1,
        "eta_in_days": 1,
        "items": [{"name_zh": "無線耳機", "name_en": "Wireless earbuds", "qty": 1, "returnable": True}],
    },
    {
        "order_id": "58210488",
        "status": "DELIVERED",
        "carrier": "SEVEN_ELEVEN",
        "ordered_days_ago": 6,
        "shipped_days_ago": 5,
        "delivered_days_ago": 3,
        "items": [{"name_zh": "帆布托特包", "name_en": "Canvas tote bag", "qty": 1, "returnable": True}],
    },
    {
        "order_id": "58210491",
        "status": "DELIVERED",
        "carrier": "BLACK_CAT",
        "ordered_days_ago": 14,
        "shipped_days_ago": 12,
        "delivered_days_ago": 10,
        "items": [{"name_zh": "陶瓷馬克杯", "name_en": "Ceramic mug", "qty": 2, "returnable": True}],
    },
    {
        "order_id": "58210502",
        "status": "DELIVERED",
        "carrier": "BLACK_CAT",
        "ordered_days_ago": 4,
        "shipped_days_ago": 3,
        "delivered_days_ago": 2,
        "items": [{"name_zh": "有機草莓禮盒", "name_en": "Organic strawberry box", "qty": 1, "returnable": False}],
    },
    {
        "order_id": "58210515",
        "status": "PROCESSING",
        "carrier": None,
        "ordered_days_ago": 1,
        "items": [{"name_zh": "慢跑鞋", "name_en": "Running shoes", "qty": 1, "returnable": True}],
    },
    {
        "order_id": "58210520",
        "status": "CANCELLED",
        "carrier": None,
        "ordered_days_ago": 3,
        "items": [{"name_zh": "藍牙喇叭", "name_en": "Bluetooth speaker", "qty": 1, "returnable": True}],
    },
]
