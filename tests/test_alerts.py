from datetime import date, timedelta

from budgets import alerts, service
from subscriptions import service as subscriptions_service

TODAY = date(2026, 10, 3)
USER_ID = 1


def sub(name="Netflix", days=10, is_trial=False, trial_started=False, last_used=None,
        price_cents=1349, category="Entertainment", price_change=None):
    """A subscription as get_active_subscriptions() returns it, with its next payment in `days` days."""
    next_payment = TODAY + timedelta(days=days)
    first_payment = next_payment
    if trial_started:
        first_payment = next_payment - timedelta(days=30)   # the first payment already happened
    return {
        "name": name,
        "category": category,
        "price_cents": price_cents,
        "monthly_cost_cents": price_cents,
        "yearly_cost_cents": price_cents * 12,
        "first_payment_date": first_payment,
        "next_payment_date": next_payment,
        "days_until_payment": days,
        "is_trial": is_trial,
        "last_used_date": last_used,
        "last_price_change": price_change,
    }


def change(old, new, days_ago):
    """A price change as the seam returns it, made `days_ago` days before TODAY."""
    return {"old_price_cents": old, "new_price_cents": new,
            "changed_date": TODAY - timedelta(days=days_ago),
            "percent": round((new - old) * 100 / old)}


# --- Free trials -----------------------------------------------------------------

def test_trial_ending_within_7_days_gives_an_alert():
    result = alerts.trial_alerts([sub("Disney+", days=7, is_trial=True)])
    assert result == [{"kind": "trial_ending", "name": "Disney+", "days": 7, "amount_cents": 1349}]


def test_trial_ending_later_or_already_paid_gives_no_alert():
    later = sub("Disney+", days=8, is_trial=True)
    already_paid = sub("Max", days=2, is_trial=True, trial_started=True)
    not_a_trial = sub("Netflix", days=1)
    assert alerts.trial_alerts([later, already_paid, not_a_trial]) == []


# --- Payments soon ---------------------------------------------------------------

def test_payment_in_3_days_or_less_gives_an_alert():
    result = alerts.payment_alerts([sub("Spotify", days=0), sub("Netflix", days=3), sub("Gym", days=4)])
    assert [(a["name"], a["days"]) for a in result] == [("Spotify", 0), ("Netflix", 3)]


def test_a_running_trial_does_not_also_get_a_payment_alert():
    running_trial = sub("Disney+", days=1, is_trial=True)
    paid_after_trial = sub("Max", days=1, is_trial=True, trial_started=True)
    result = alerts.payment_alerts([running_trial, paid_after_trial])
    assert [a["name"] for a in result] == ["Max"]


# --- Unused subscriptions ---------------------------------------------------------

def test_not_used_for_30_days_or_more_gives_an_alert():
    unused = sub("Gym", last_used=(TODAY - timedelta(days=30)).isoformat())
    recent = sub("Spotify", last_used=(TODAY - timedelta(days=29)).isoformat())
    never_filled_in = sub("Netflix", last_used=None)
    result = alerts.unused_alerts([unused, recent, never_filled_in], TODAY)
    assert result == [{"kind": "unused", "name": "Gym", "days": 30, "amount_cents": 1349}]


# --- Budgets ------------------------------------------------------------------------

def test_only_categories_over_budget_give_an_alert():
    rows = service.build_report(
        [sub("Netflix", price_cents=2500), sub("Spotify", price_cents=900, category="Music")],
        {"Entertainment": 2000, "Music": 1000},
    )
    result = alerts.budget_alerts(rows)
    assert result == [{"kind": "over_budget", "name": "Entertainment",
                       "amount_cents": 2500, "limit_cents": 2000}]


# --- All alerts together -------------------------------------------------------------

def test_alerts_come_most_urgent_kind_first():
    subscriptions = [
        sub("Gym", days=20, last_used="2026-08-01", category="Health & Fitness"),
        sub("Netflix", days=2, price_cents=2500),
        sub("Disney+", days=5, is_trial=True),
    ]
    rows = service.build_report(subscriptions, {"Entertainment": 2000})
    kinds = [a["kind"] for a in alerts.build_alerts(subscriptions, rows, TODAY)]
    assert kinds == ["trial_ending", "over_budget", "payment_soon", "unused"]


def test_no_subscriptions_means_no_alerts():
    assert alerts.build_alerts([], [], TODAY) == []


def test_get_alerts_reads_the_users_own_data(temp_db):
    form = {"name": "Netflix", "category": "Entertainment", "price": "13.49", "billing_cycle": "monthly",
            "first_payment_date": "2026-10-05", "last_used_date": "2026-08-01"}
    subscriptions_service.create_subscription(USER_ID, form, TODAY)
    service.set_budget(USER_ID, {"category": "Entertainment", "amount": "10"})

    kinds = [a["kind"] for a in alerts.get_alerts(USER_ID, TODAY)]
    assert kinds == ["over_budget", "payment_soon", "unused"]
    assert alerts.get_alerts(2, TODAY) == []


# --- Price rises ---------------------------------------------------------------------

def test_price_rise_in_the_last_30_days_gives_an_alert():
    result = alerts.price_rise_alerts([sub("Netflix", price_change=change(1349, 1599, 30))], TODAY)
    assert result == [{"kind": "price_rise", "name": "Netflix", "old_cents": 1349, "amount_cents": 1599,
                       "percent": 19, "date": TODAY - timedelta(days=30)}]


def test_old_price_rises_drops_and_no_change_give_no_alert():
    subscriptions = [
        sub("Netflix", price_change=change(1349, 1599, 31)),
        sub("Spotify", price_change=change(1099, 999, 2)),
        sub("Gym"),
    ]
    assert alerts.price_rise_alerts(subscriptions, TODAY) == []


def test_price_rise_comes_after_budgets_and_before_payments():
    subscriptions = [
        sub("Netflix", days=2, price_cents=2500, price_change=change(2000, 2500, 1)),
        sub("Disney+", days=5, is_trial=True),
    ]
    rows = service.build_report(subscriptions, {"Entertainment": 2000})
    kinds = [a["kind"] for a in alerts.build_alerts(subscriptions, rows, TODAY)]
    assert kinds == ["trial_ending", "over_budget", "price_rise", "payment_soon"]
