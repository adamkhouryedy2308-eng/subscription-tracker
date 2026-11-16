"""Integration tests for /budgets: Flask, the routes, the service and a real (temporary) database.

The Subscriptions service is replaced by the fake_subscriptions stub (see conftest.py).
"""
from datetime import date, timedelta

import pytest

import app as app_module
from tests.conftest import log_in_as, make_token


def netflix(price_cents=1349):
    """Netflix as GET /subscriptions/active returns it (after the dates are turned back into dates)."""
    next_payment = date.today() + timedelta(days=10)
    return {"name": "Netflix", "category": "Entertainment", "price_cents": price_cents,
            "monthly_cost_cents": price_cents, "yearly_cost_cents": price_cents * 12,
            "first_payment_date": next_payment, "next_payment_date": next_payment,
            "days_until_payment": 10, "is_trial": False, "last_used_date": None,
            "last_price_change": None}


def test_requests_without_a_token_get_401(guest, fake_subscriptions):
    for url in ["/budgets", "/alerts"]:
        response = guest.get(url)
        assert response.status_code == 401
        assert response.get_json()["error"] == "Log in first."


def test_a_token_stamped_with_another_key_is_refused(guest, fake_subscriptions):
    guest.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {make_token(1, key='some-other-key')}"
    assert guest.get("/budgets").status_code == 401


def test_the_header_must_start_with_bearer(guest, fake_subscriptions):
    guest.environ_base["HTTP_AUTHORIZATION"] = "Basic something"
    assert guest.get("/budgets").status_code == 401


def test_empty_budgets(client, fake_subscriptions):
    data = client.get("/budgets").get_json()
    assert data["spending_available"] is True
    assert data["rows"] == []
    assert data["budgets"] == {}
    assert len(data["categories"]) == 10


def test_spending_per_category(client, fake_subscriptions):
    fake_subscriptions["subscriptions"] = [netflix()]
    row = client.get("/budgets").get_json()["rows"][0]
    assert row["category"] == "Entertainment"
    assert row["monthly_cents"] == 1349
    assert row["yearly_cents"] == 16188
    assert row["status"] == "none"


def test_saving_a_budget_shows_how_much_is_used(client, fake_subscriptions):
    fake_subscriptions["subscriptions"] = [netflix()]
    response = client.post("/budgets", json={"category": "Entertainment", "amount": "20"})
    assert response.status_code == 200
    row = client.get("/budgets").get_json()["rows"][0]
    assert row["budget_cents"] == 2000
    assert row["used_percent"] == 67
    assert row["status"] == "ok"


def test_going_over_budget(client, fake_subscriptions):
    fake_subscriptions["subscriptions"] = [netflix()]
    client.post("/budgets", json={"category": "Entertainment", "amount": "10"})
    data = client.get("/budgets").get_json()
    assert data["rows"][0]["status"] == "over"
    assert data["summary"]["over_budget"] == ["Entertainment"]


def test_saving_a_wrong_budget_gives_the_errors(client, fake_subscriptions):
    response = client.post("/budgets", json={"category": "Music", "amount": "lots"})
    assert response.status_code == 400
    assert "Budget must be a number, like 25 or 12.50." in response.get_json()["errors"]


def test_removing_a_budget(client, fake_subscriptions):
    client.post("/budgets", json={"category": "Music", "amount": "15"})
    assert client.post("/budgets/remove", json={"category": "Music"}).status_code == 200
    assert client.get("/budgets").get_json()["budgets"] == {}


def test_remove_only_works_with_post(client, fake_subscriptions):
    response = client.get("/budgets/remove")
    assert response.status_code == 405
    assert response.get_json()["error"]


def test_unknown_addresses_answer_json(client):
    response = client.get("/nothing-here")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Not found."


def test_other_users_never_see_my_budgets(client, fake_subscriptions):
    client.post("/budgets", json={"category": "Music", "amount": "15"})
    log_in_as(client, 2)
    assert client.get("/budgets").get_json()["budgets"] == {}


# --- Partial failure: the Subscriptions service is down -------------------------------

def test_budgets_still_work_when_subscriptions_is_down(client, fake_subscriptions):
    fake_subscriptions["down"] = True
    assert client.post("/budgets", json={"category": "Music", "amount": "15"}).status_code == 200

    response = client.get("/budgets")
    data = response.get_json()
    assert response.status_code == 200
    assert data["spending_available"] is False
    assert "Subscriptions service is not answering" in data["message"]
    assert data["budgets"] == {"Music": 1500}


def test_the_service_refuses_to_start_without_a_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        app_module.get_secret_key()
