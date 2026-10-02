from datetime import date

import pytest
from fastapi.testclient import TestClient

import repository
import returns
from api import app
from normalize import normalize_order_id, normalize_phone_last4

SECRET = "test-secret"
TODAY = date(2026, 10, 2)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TOOL_SECRET", SECRET)
    monkeypatch.setattr(repository, "today_taipei", lambda: TODAY)
    return TestClient(app)


def post(client, path, order_id, phone="0912", secret=SECRET):
    headers = {"X-Tool-Secret": secret} if secret else {}
    return client.post(path, json={"order_id": order_id, "phone_last4": phone}, headers=headers)


# --- normalize -------------------------------------------------------------

@pytest.mark.parametrize("raw", [
    "58210473",
    "5821 0473",
    "5821-0473",
    "５８２１０４７３",
    "五八二一零四七三",
    "五八二幺洞四拐三",
    "五八二一 0473",
])
def test_order_id_variants(raw):
    assert normalize_order_id(raw) == "58210473"


@pytest.mark.parametrize("raw", ["", "5821047", "582104731", "abc"])
def test_order_id_invalid(raw):
    assert normalize_order_id(raw) is None


def test_phone_last4():
    assert normalize_phone_last4("零九一二") == "0912"
    assert normalize_phone_last4("912") is None


# --- return rules ----------------------------------------------------------

def _delivered(days_ago, returnable=True):
    return {
        "status": "DELIVERED",
        "delivered_at": date.fromordinal(TODAY.toordinal() - days_ago),
        "items": [{"name_en": "Thing", "returnable": returnable}],
    }


def test_day_7_is_still_returnable():
    assert returns.decide(_delivered(7), TODAY).eligible is True


def test_day_8_is_expired():
    d = returns.decide(_delivered(8), TODAY)
    assert (d.eligible, d.reason_code) == (False, "WINDOW_EXPIRED")


def test_non_returnable_item():
    d = returns.decide(_delivered(1, returnable=False), TODAY)
    assert d.reason_code == "NON_RETURNABLE_ITEM"


# --- endpoints -------------------------------------------------------------

def test_order_status_shipped(client):
    r = post(client, "/tools/order-status", "58210473")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["status"] == "SHIPPED"
    assert body["eta"] == "2026-10-03"


def test_order_status_accepts_spoken_chinese_digits(client):
    body = post(client, "/tools/order-status", "五八二一零四七三", phone="零九一二").json()
    assert body["ok"] is True


@pytest.mark.parametrize("order_id, eligible, reason", [
    ("58210488", True, "WITHIN_WINDOW"),
    ("58210491", False, "WINDOW_EXPIRED"),
    ("58210502", False, "NON_RETURNABLE_ITEM"),
    ("58210515", False, "NOT_DELIVERED"),
    ("58210520", False, "CANCELLED"),
])
def test_return_eligibility_scenarios(client, order_id, eligible, reason):
    body = post(client, "/tools/return-eligibility", order_id).json()
    assert (body["eligible"], body["reason_code"]) == (eligible, reason)


def test_expired_order_deadline(client):
    body = post(client, "/tools/return-eligibility", "58210491").json()
    assert body["delivered_at"] == "2026-09-22"
    assert body["return_deadline"] == "2026-09-29"


def test_wrong_phone_looks_like_unknown_order(client):
    wrong_phone = post(client, "/tools/order-status", "58210473", phone="1234").json()
    unknown = post(client, "/tools/order-status", "99999999").json()
    assert wrong_phone == unknown == {"ok": False, "error_code": "ORDER_NOT_FOUND"}


def test_invalid_order_id(client):
    body = post(client, "/tools/order-status", "123").json()
    assert body == {"ok": False, "error_code": "INVALID_ORDER_ID"}


@pytest.mark.parametrize("secret", [None, "wrong"])
def test_rejects_bad_secret(client, secret):
    assert post(client, "/tools/order-status", "58210473", secret=secret).status_code == 401


def test_health(client):
    assert client.get("/health").json() == {"ok": True}
