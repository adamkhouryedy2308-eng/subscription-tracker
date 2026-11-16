"""Integration tests for /alerts, with the Subscriptions service replaced by the fake_subscriptions stub."""
from datetime import date, timedelta

from tests.conftest import log_in_as
from tests.test_budgets_pages import netflix


def test_no_subscriptions_means_no_alerts(client, fake_subscriptions):
    data = client.get("/alerts").get_json()
    assert data["alerts"] == []
    assert data["payment_soon_days"] == 3


def test_every_kind_of_alert_in_order(client, fake_subscriptions):
    today = date.today()
    soon = dict(netflix(), next_payment_date=today + timedelta(days=1), days_until_payment=1,
                last_used_date=(today - timedelta(days=40)).isoformat())
    trial = dict(netflix(899), name="Disney+", is_trial=True, first_payment_date=today,
                 next_payment_date=today, days_until_payment=0)
    rise = dict(netflix(1599), name="Max", last_price_change={
        "old_price_cents": 1349, "new_price_cents": 1599, "changed_date": today, "percent": 19})
    fake_subscriptions["subscriptions"] = [soon, trial, rise]
    client.post("/budgets", json={"category": "Entertainment", "amount": "15"})

    data = client.get("/alerts").get_json()
    kinds = [alert["kind"] for alert in data["alerts"]]
    assert kinds == ["trial_ending", "over_budget", "price_rise", "payment_soon", "unused"]
    assert data["alerts"][2]["date"] == today.isoformat()  # dates travel as text


def test_budgets_of_other_users_never_make_my_alerts(client, fake_subscriptions):
    fake_subscriptions["subscriptions"] = [netflix()]
    client.post("/budgets", json={"category": "Entertainment", "amount": "5"})
    log_in_as(client, 2)
    assert client.get("/alerts").get_json()["alerts"] == []


def test_alerts_give_a_clear_503_when_subscriptions_is_down(client, fake_subscriptions):
    fake_subscriptions["down"] = True
    response = client.get("/alerts")
    assert response.status_code == 503
    assert "Subscriptions service is not answering" in response.get_json()["error"]
