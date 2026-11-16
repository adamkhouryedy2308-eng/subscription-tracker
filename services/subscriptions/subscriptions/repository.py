"""SQL for the subscriptions table. Only this file reads or writes that table."""
import db

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
    billing_cycle TEXT NOT NULL
        CHECK (billing_cycle IN ('weekly', 'monthly', 'quarterly', 'yearly')),
    first_payment_date TEXT NOT NULL,
    is_trial INTEGER NOT NULL DEFAULT 0,
    last_used_date TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'cancelled')),
    cancelled_date TEXT
)
"""

CREATE_PRICE_CHANGES_TABLE = """
CREATE TABLE IF NOT EXISTS price_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER NOT NULL REFERENCES subscriptions (id),
    old_price_cents INTEGER NOT NULL,
    new_price_cents INTEGER NOT NULL,
    changed_date TEXT NOT NULL
)
"""


def add_subscription(user_id, sub):
    """Save a new subscription for this user and return its id."""
    conn = db.get_connection()
    cursor = conn.execute(
        """
        INSERT INTO subscriptions
            (user_id, name, category, price_cents, billing_cycle,
             first_payment_date, is_trial, last_used_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def update_subscription(user_id, subscription_id, sub):
    """Save new values over one of this user's subscriptions."""
    conn = db.get_connection()
    conn.execute(
        """
        UPDATE subscriptions
        SET name = ?, category = ?, price_cents = ?, billing_cycle = ?,
            first_payment_date = ?, is_trial = ?, last_used_date = ?
        WHERE id = ? AND user_id = ?
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
    conn.commit()
    conn.close()


def cancel_subscription(user_id, subscription_id, cancelled_date):
    """Mark one of this user's active subscriptions as cancelled. The row is kept for the history."""
    conn = db.get_connection()
    conn.execute(
        """
        UPDATE subscriptions
        SET status = 'cancelled', cancelled_date = ?
        WHERE id = ? AND user_id = ? AND status = 'active'
        """,
        (cancelled_date, subscription_id, user_id),
    )
    conn.commit()
    conn.close()


def list_subscriptions(user_id, status="active"):
    """Return this user's subscriptions with the given status, sorted by name."""
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT * FROM subscriptions WHERE user_id = ? AND status = ? ORDER BY name",
        (user_id, status),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_subscription(user_id, subscription_id):
    """Return one of this user's subscriptions as a dict, or None if it is not theirs or does not exist."""
    conn = db.get_connection()
    row = conn.execute(
        "SELECT * FROM subscriptions WHERE id = ? AND user_id = ?",
        (subscription_id, user_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def add_price_change(subscription_id, old_price_cents, new_price_cents, changed_date):
    """Remember that a subscription's price changed."""
    conn = db.get_connection()
    conn.execute(
        """
        INSERT INTO price_changes (subscription_id, old_price_cents, new_price_cents, changed_date)
        VALUES (?, ?, ?, ?)
        """,
        (subscription_id, old_price_cents, new_price_cents, changed_date),
    )
    conn.commit()
    conn.close()


def list_price_changes(subscription_id):
    """Every price change of one subscription, oldest first."""
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT * FROM price_changes WHERE subscription_id = ? ORDER BY changed_date, id",
        (subscription_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
