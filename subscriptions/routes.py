"""Web pages for the subscriptions domain."""
from datetime import date

from flask import Blueprint, abort, redirect, render_template, request, session, url_for

from subscriptions import service

bp = Blueprint("subscriptions", __name__, url_prefix="/subscriptions")

# The message shown on the list page after each action, e.g. ?added=Netflix
NOTICES = {
    "added": "was added to your subscriptions.",
    "updated": "was updated.",
    "cancelled": "was cancelled. You can still see it under Cancelled.",
}


@bp.route("/")
def list_page():
    """Show the totals, every active subscription and the cancelled ones."""
    user_id = session["user_id"]
    subscriptions = service.get_active_subscriptions(user_id, date.today())
    cancelled = service.get_cancelled_subscriptions(user_id)

    notice = None
    for action, text in NOTICES.items():
        if request.args.get(action):
            notice = {"name": request.args[action], "text": text}

    return render_template(
        "subscriptions/list.html",
        subscriptions=subscriptions,
        summary=service.summarise(subscriptions),
        cancelled=cancelled,
        yearly_savings=service.yearly_savings_cents(cancelled),
        notice=notice,
    )


@bp.route("/new", methods=["GET", "POST"])
def add_page():
    """GET shows an empty form; POST checks it and saves it."""
    title = "Add a subscription"
    subtitle = "It takes 20 seconds. You can change anything later."
    if request.method == "POST":
        user_id = session["user_id"]
        new_id, errors = service.create_subscription(user_id, request.form, date.today())
        if not errors:
            name = request.form["name"].strip()
            return redirect(url_for("subscriptions.list_page", added=name))
        return render_form(title, subtitle, request.form, errors), 400
    return render_form(title, subtitle, {}, [])


@bp.route("/<int:subscription_id>/edit", methods=["GET", "POST"])
def edit_page(subscription_id):
    """GET shows the form filled in; POST checks the changes and saves them."""
    user_id = session["user_id"]
    sub = service.get_subscription(user_id, subscription_id)
    if sub is None or sub["status"] != "active":
        abort(404)

    title = f"Edit {sub['name']}"
    subtitle = "Change what you need and save."
    if request.method == "POST":
        errors = service.update_subscription(user_id, subscription_id, request.form, date.today())
        if not errors:
            name = request.form["name"].strip()
            return redirect(url_for("subscriptions.list_page", updated=name))
        return render_form(title, subtitle, request.form, errors), 400
    history = service.get_price_history(user_id, subscription_id)
    return render_form(title, subtitle, service.subscription_to_form(sub), [], history)


@bp.route("/<int:subscription_id>/cancel", methods=["POST"])
def cancel(subscription_id):
    """Cancel a subscription. Only POST is allowed, because it changes data."""
    user_id = session["user_id"]
    sub = service.get_subscription(user_id, subscription_id)
    if sub is None:
        abort(404)
    service.cancel_subscription(user_id, subscription_id, date.today())
    return redirect(url_for("subscriptions.list_page", cancelled=sub["name"]))


def render_form(title, subtitle, form, errors, history=None):
    """Show the subscription form with the values typed so far, any errors and the price history."""
    return render_template(
        "subscriptions/form.html",
        title=title,
        subtitle=subtitle,
        form=form,
        errors=errors,
        categories=service.CATEGORIES,
        billing_cycles=service.CYCLES_PER_YEAR,
        history=history or [],
    )
