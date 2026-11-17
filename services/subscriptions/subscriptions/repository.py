"""SQL for the subscriptions and price_changes tables. Only this file reads or writes them.

The tables themselves are created by migrations/001_init.sql.
"""
import db


def add_subscription(user_id, sub):
    """Save a new subscription for this user and return its id."""
    return db.insert(
        """
        INSERT INTO subscriptions
            (user_id, name, category, price_cents, billing_cycle,
             first_payment_date, is_trial, last_used_date)
        OUTPUT INSERTED.id
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            sub["name"],
            sub["category"],
            sub["price_cents"],
            sub["billing_cycle"],
            sub["first_payment_date"],
            sub["is_trial"],
            sub["last_used_date"],
        ),
    )


def update_subscription(user_id, subscription_id, sub):
    """Save new values over one of this user's subscriptions."""
    db.execute(
        """
        UPDATE subscriptions
        SET name = %s, category = %s, price_cents = %s, billing_cycle = %s,
            first_payment_date = %s, is_trial = %s, last_used_date = %s
        WHERE id = %s AND user_id = %s
        """,
        (
            sub["name"],
            sub["category"],
            sub["price_cents"],
            sub["billing_cycle"],
            sub["first_payment_date"],
            sub["is_trial"],
            sub["last_used_date"],
            subscription_id,
            user_id,
        ),
    )


def cancel_subscription(user_id, subscription_id, cancelled_date):
    """Mark one of this user's active subscriptions as cancelled. The row is kept for the history."""
    db.execute(
        """
        UPDATE subscriptions
        SET status = 'cancelled', cancelled_date = %s
        WHERE id = %s AND user_id = %s AND status = 'active'
        """,
        (cancelled_date, subscription_id, user_id),
    )


def list_subscriptions(user_id, status="active"):
    """Return this user's subscriptions with the given status, sorted by name."""
    return db.query(
        "SELECT * FROM subscriptions WHERE user_id = %s AND status = %s ORDER BY name",
        (user_id, status),
    )


def get_subscription(user_id, subscription_id):
    """Return one of this user's subscriptions as a dict, or None if it is not theirs or does not exist."""
    return db.query_one(
        "SELECT * FROM subscriptions WHERE id = %s AND user_id = %s",
        (subscription_id, user_id),
    )


def add_price_change(subscription_id, old_price_cents, new_price_cents, changed_date):
    """Remember that a subscription's price changed."""
    db.execute(
        """
        INSERT INTO price_changes (subscription_id, old_price_cents, new_price_cents, changed_date)
        VALUES (%s, %s, %s, %s)
        """,
        (subscription_id, old_price_cents, new_price_cents, changed_date),
    )


def list_price_changes(subscription_id):
    """Every price change of one subscription, oldest first."""
    return db.query(
        "SELECT * FROM price_changes WHERE subscription_id = %s ORDER BY changed_date, id",
        (subscription_id,),
    )
