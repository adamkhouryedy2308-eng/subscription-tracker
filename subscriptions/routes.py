"""Web pages for the subscriptions domain."""
from datetime import date

from flask import Blueprint, redirect, render_template, request, url_for

from subscriptions import service

bp = Blueprint("subscriptions", __name__, url_prefix="/subscriptions")


@bp.route("/")
def list_page():
    """Show the totals and every active subscription."""
    subscriptions = service.get_active_subscriptions(date.today())
    return render_template(
        "subscriptions/list.html",
        subscriptions=subscriptions,
        summary=service.summarise(subscriptions),
        added=request.args.get("added"),
    )


@bp.route("/new", methods=["GET", "POST"])
def add_page():
    """GET shows an empty form; POST checks it and saves it."""
    if request.method == "POST":
        new_id, errors = service.create_subscription(request.form, date.today())
        if not errors:
            name = request.form["name"].strip()
            return redirect(url_for("subscriptions.list_page", added=name))
        return render_form("Add a subscription", request.form, errors), 400
    return render_form("Add a subscription", {}, [])


def render_form(title, form, errors):
    """Show the subscription form with the values typed so far and any errors."""
    return render_template(
        "subscriptions/form.html",
        title=title,
        form=form,
        errors=errors,
        categories=service.CATEGORIES,
        billing_cycles=service.CYCLES_PER_YEAR,
    )
