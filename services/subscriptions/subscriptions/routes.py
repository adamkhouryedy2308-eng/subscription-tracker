"""Subscription endpoints. Every answer is JSON; the static pages in ui/ draw it."""
from datetime import date

from flask import Blueprint, g, jsonify, request

from subscriptions import bank_import, service

bp = Blueprint("subscriptions", __name__, url_prefix="/subscriptions")


@bp.route("", methods=["GET"])
def list_all():
    """The totals, every active subscription and the cancelled ones."""
    user_id = g.user["id"]
    subscriptions = service.get_active_subscriptions(user_id, date.today())
    cancelled = service.get_cancelled_subscriptions(user_id)
    return jsonify(
        subscriptions=subscriptions,
        summary=service.summarise(subscriptions),
        cancelled=cancelled,
        yearly_savings_cents=service.yearly_savings_cents(cancelled),
    )


@bp.route("/active", methods=["GET"])
def active():
    """THE SEAM: the one endpoint the Budgets service calls to read subscription data.

    It is get_active_subscriptions() from Assignment 1, now reached over HTTP.
    """
    return jsonify(subscriptions=service.get_active_subscriptions(g.user["id"], date.today()))


@bp.route("/options", methods=["GET"])
def options():
    """The choices for the form: the 10 categories and the 4 billing cycles."""
    return jsonify(categories=service.CATEGORIES, billing_cycles=list(service.CYCLES_PER_YEAR))


@bp.route("", methods=["POST"])
def add():
    """Check a new subscription and save it (201 = created)."""
    form = request.get_json(silent=True) or {}
    new_id, errors = service.create_subscription(g.user["id"], form, date.today())
    if errors:
        return jsonify(errors=errors), 400
    return jsonify(id=new_id), 201


@bp.route("/<int:subscription_id>", methods=["GET"])
def get_one(subscription_id):
    """One active subscription as form values, plus its price history (for the edit page)."""
    user_id = g.user["id"]
    sub = service.get_subscription(user_id, subscription_id)
    if sub is None or sub["status"] != "active":
        return jsonify(error="Subscription not found."), 404
    return jsonify(
        id=subscription_id,
        form=service.subscription_to_form(sub),
        history=service.get_price_history(user_id, subscription_id),
    )


@bp.route("/<int:subscription_id>", methods=["PUT"])
def edit(subscription_id):
    """Save changes to one active subscription. PUT = replace it with these values."""
    user_id = g.user["id"]
    sub = service.get_subscription(user_id, subscription_id)
    if sub is None or sub["status"] != "active":
        return jsonify(error="Subscription not found."), 404
    form = request.get_json(silent=True) or {}
    errors = service.update_subscription(user_id, subscription_id, form, date.today())
    if errors:
        return jsonify(errors=errors), 400
    return jsonify(id=subscription_id)


@bp.route("/<int:subscription_id>/cancel", methods=["POST"])
def cancel(subscription_id):
    """Cancel a subscription (it is kept, marked cancelled). Only POST, because it changes data."""
    user_id = g.user["id"]
    sub = service.get_subscription(user_id, subscription_id)
    if sub is None:
        return jsonify(error="Subscription not found."), 404
    service.cancel_subscription(user_id, subscription_id, date.today())
    return jsonify(id=subscription_id, name=sub["name"])


@bp.route("/import", methods=["POST"])
def import_statement():
    """Read an uploaded bank statement and suggest the payments that repeat.

    The file is only read in memory: neither the file nor its payments are saved.
    """
    file = request.files.get("statement")
    if file is None or not file.filename:
        return import_error("Choose a CSV file from your bank first.")
    if not file.filename.lower().endswith(".csv"):
        return import_error("The file must be a .csv export from your bank.")
    try:
        text = file.read().decode("utf-8-sig")
        payments, skipped = bank_import.read_statement(text)
    except UnicodeDecodeError:
        return import_error("The file could not be read. Export it from your bank as CSV.")
    except ValueError as error:
        return import_error(str(error))

    tracked = [sub["name"] for sub in service.get_active_subscriptions(g.user["id"], date.today())]
    return jsonify(
        suggestions=bank_import.find_recurring(payments, tracked),
        payment_count=len(payments),
        skipped=skipped,
    )


@bp.route("/import/confirm", methods=["POST"])
def confirm_import():
    """Add the suggestions the user ticked, checked by the same validate() as the add form."""
    items = (request.get_json(silent=True) or {}).get("items", [])
    added = 0
    for form in items:
        new_id, errors = service.create_subscription(g.user["id"], form, date.today())
        if not errors:
            added += 1
    return jsonify(added=added)


def import_error(message):
    """Answer 400 with one error message about the uploaded file."""
    return jsonify(errors=[message]), 400
