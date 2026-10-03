"""Web pages for the Budgets & Alerts domain."""
from datetime import date

from flask import Blueprint, g, redirect, render_template, request, session, url_for

from budgets import alerts, service
from subscriptions import service as subscriptions_service

bp = Blueprint("budgets", __name__, url_prefix="/budgets")


@bp.route("/", methods=["GET", "POST"])
def budgets_page():
    """GET shows spending per category and the budgets; POST saves a budget."""
    user_id = session["user_id"]
    errors = []
    form = {}
    if request.method == "POST":
        errors = service.set_budget(user_id, request.form)
        if not errors:
            return redirect(url_for("budgets.budgets_page", saved=request.form["category"]))
        form = request.form

    rows = service.get_budget_report(user_id, date.today())
    page = render_template(
        "budgets/budgets.html",
        rows=rows,
        summary=service.summarise_report(rows),
        categories=subscriptions_service.CATEGORIES,
        form=form,
        errors=errors,
        saved=request.args.get("saved"),
        removed=request.args.get("removed"),
    )
    if errors:
        return page, 400
    return page


@bp.route("/remove", methods=["POST"])
def remove():
    """Remove the budget of one category. Only POST, because it changes data."""
    category = request.form.get("category", "")
    service.remove_budget(session["user_id"], category)
    return redirect(url_for("budgets.budgets_page", removed=category))


@bp.route("/alerts")
def alerts_page():
    """Show every alert for the logged-in user, most urgent kind first."""
    return render_template(
        "budgets/alerts.html",
        alerts=alerts.get_alerts(session["user_id"], date.today()),
        payment_soon_days=alerts.PAYMENT_SOON_DAYS,
        trial_warning_days=alerts.TRIAL_WARNING_DAYS,
        unused_days=alerts.UNUSED_DAYS,
        price_rise_days=alerts.PRICE_RISE_DAYS,
    )


@bp.app_context_processor
def alert_count():
    """Runs before every page is drawn: the number of alerts, for the badge in the sidebar."""
    if g.get("user") is None:
        return {"alert_count": 0}
    return {"alert_count": len(alerts.get_alerts(g.user["id"], date.today()))}
