"""Alerts: the warnings shown on the dashboard, worked out from subscriptions and budgets."""
from datetime import date

from budgets import repository, service
from subscriptions import service as subscriptions_service

PAYMENT_SOON_DAYS = 3    # warn when a payment is this many days away or less
TRIAL_WARNING_DAYS = 7   # warn this many days before a free trial turns into a paid plan
UNUSED_DAYS = 30         # warn when a subscription has not been used for this many days


def trial_still_running(sub):
    """A free trial whose first payment has not happened yet."""
    return sub["is_trial"] and sub["next_payment_date"] == sub["first_payment_date"]


def trial_alerts(subscriptions):
    """One alert per free trial that turns into a paid plan soon."""
    alerts = []
    for sub in subscriptions:
        if trial_still_running(sub) and sub["days_until_payment"] <= TRIAL_WARNING_DAYS:
            alerts.append({
                "kind": "trial_ending",
                "name": sub["name"],
                "days": sub["days_until_payment"],
                "amount_cents": sub["price_cents"],
            })
    return alerts


def budget_alerts(report_rows):
    """One alert per category that costs more than its budget."""
    alerts = []
    for row in report_rows:
        if row["status"] == "over":
            alerts.append({
                "kind": "over_budget",
                "name": row["category"],
                "amount_cents": row["monthly_cents"],
                "limit_cents": row["budget_cents"],
            })
    return alerts


def payment_alerts(subscriptions):
    """One alert per payment in the next few days (trials already have their own alert)."""
    alerts = []
    for sub in subscriptions:
        if sub["days_until_payment"] <= PAYMENT_SOON_DAYS and not trial_still_running(sub):
            alerts.append({
                "kind": "payment_soon",
                "name": sub["name"],
                "days": sub["days_until_payment"],
                "amount_cents": sub["price_cents"],
            })
    return alerts


def unused_alerts(subscriptions, today):
    """One alert per subscription that has not been used for a long time."""
    alerts = []
    for sub in subscriptions:
        if not sub["last_used_date"]:
            continue
        days_unused = (today - date.fromisoformat(sub["last_used_date"])).days
        if days_unused >= UNUSED_DAYS:
            alerts.append({
                "kind": "unused",
                "name": sub["name"],
                "days": days_unused,
                "amount_cents": sub["monthly_cost_cents"],
            })
    return alerts


def build_alerts(subscriptions, report_rows, today):
    """Every alert, most urgent kind first: trials, budgets, payments, unused."""
    return (
        trial_alerts(subscriptions)
        + budget_alerts(report_rows)
        + payment_alerts(subscriptions)
        + unused_alerts(subscriptions, today)
    )


def get_alerts(user_id, today):
    """The alerts for one user. Subscriptions come only through the seam (ADR-2)."""
    subscriptions = subscriptions_service.get_active_subscriptions(user_id, today)
    report_rows = service.build_report(subscriptions, repository.list_budgets(user_id))
    return build_alerts(subscriptions, report_rows, today)
