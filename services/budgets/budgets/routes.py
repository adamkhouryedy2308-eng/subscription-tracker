"""Budgets & Alerts endpoints. Every answer is JSON; the static pages in ui/ draw it."""
from datetime import date

from flask import Blueprint, g, jsonify, request

import auth
import subscriptions_client
from budgets import alerts, service

bp = Blueprint("budgets", __name__)

SPENDING_UNAVAILABLE = ("Spending is unavailable right now because the Subscriptions service "
                        "is not answering. Your budgets are safe. Try again in a minute.")
ALERTS_UNAVAILABLE = ("Alerts are unavailable right now because the Subscriptions service "
                      "is not answering. Try again in a minute.")


# Endpoints anyone may call without logging in. Every other one needs a token.
PUBLIC_ENDPOINTS = ["health"]


@bp.before_app_request
def require_login():
    """Runs before every request: check the token's stamp, or answer 401 (not logged in)."""
    g.token = auth.token_from_request()
    g.user_id = auth.read_token(g.token) if g.token else None
    if request.method == "OPTIONS":   # the browser's CORS question carries no token
        return None
    if g.user_id is None and request.endpoint not in PUBLIC_ENDPOINTS:
        return jsonify(error="Log in first."), 401


@bp.route("/budgets", methods=["GET"])
def budgets_report():
    """Spending per category next to each budget.

    If Subscriptions is down, the budgets themselves are still shown (they live
    in this service), with a message instead of the spending.
    """
    budgets = service.list_budgets(g.user_id)
    try:
        subscriptions = subscriptions_client.get_active_subscriptions(g.token)
    except subscriptions_client.SubscriptionsUnavailable:
        return jsonify(spending_available=False, message=SPENDING_UNAVAILABLE,
                       budgets=budgets, categories=service.CATEGORIES)

    rows = service.get_budget_report(g.user_id, subscriptions)
    return jsonify(spending_available=True, rows=rows, summary=service.summarise_report(rows),
                   budgets=budgets, categories=service.CATEGORIES)


@bp.route("/budgets", methods=["POST"])
def save_budget():
    """Save (or change) the monthly budget of one category. Works without Subscriptions."""
    form = request.get_json(silent=True) or {}
    errors = service.set_budget(g.user_id, form)
    if errors:
        return jsonify(errors=errors), 400
    return jsonify(category=form["category"])


@bp.route("/budgets/remove", methods=["POST"])
def remove():
    """Remove the budget of one category. Only POST, because it changes data."""
    category = (request.get_json(silent=True) or {}).get("category", "")
    service.remove_budget(g.user_id, category)
    return jsonify(category=category)


@bp.route("/alerts", methods=["GET"])
def alerts_list():
    """Every alert for the logged-in user, most urgent kind first.

    Alerts are worked out from subscriptions, so without Subscriptions there are
    none to show: answer 503 (service unavailable) with a clear message.
    """
    try:
        subscriptions = subscriptions_client.get_active_subscriptions(g.token)
    except subscriptions_client.SubscriptionsUnavailable:
        return jsonify(error=ALERTS_UNAVAILABLE), 503
    return jsonify(
        alerts=alerts.get_alerts(g.user_id, subscriptions, date.today()),
        payment_soon_days=alerts.PAYMENT_SOON_DAYS,
        trial_warning_days=alerts.TRIAL_WARNING_DAYS,
        unused_days=alerts.UNUSED_DAYS,
        price_rise_days=alerts.PRICE_RISE_DAYS,
    )
