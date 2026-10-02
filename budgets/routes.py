"""Web pages for the Budgets & Alerts domain."""
from datetime import date

from flask import Blueprint, redirect, render_template, request, session, url_for

from budgets import service
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
