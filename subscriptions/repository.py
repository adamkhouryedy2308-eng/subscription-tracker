"""SQL for the subscriptions table. Only this file reads or writes that table."""
import db

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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


def add_subscription(sub):
    """Save a new subscription and return its id."""
    conn = db.get_connection()
    cursor = conn.execute(
        """
        INSERT INTO subscriptions
            (name, category, price_cents, billing_cycle,
             first_payment_date, is_trial, last_used_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
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


def update_subscription(subscription_id, sub):
    """Save new values over an existing subscription."""
    conn = db.get_connection()
    conn.execute(
        """
        UPDATE subscriptions
        SET name = ?, category = ?, price_cents = ?, billing_cycle = ?,
            first_payment_date = ?, is_trial = ?, last_used_date = ?
        WHERE id = ?
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
        ),
    )
    conn.commit()
    conn.close()


def cancel_subscription(subscription_id, cancelled_date):
    """Mark an active subscription as cancelled. The row is kept for the history."""
    conn = db.get_connection()
    conn.execute(
        """
        UPDATE subscriptions
        SET status = 'cancelled', cancelled_date = ?
        WHERE id = ? AND status = 'active'
        """,
        (cancelled_date, subscription_id),
    )
    conn.commit()
    conn.close()


def list_subscriptions(status="active"):
    """Return every subscription with the given status, sorted by name."""
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT * FROM subscriptions WHERE status = ? ORDER BY name",
        (status,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_subscription(subscription_id):
    """Return one subscription as a dict, or None if the id does not exist."""
    conn = db.get_connection()
    row = conn.execute(
        "SELECT * FROM subscriptions WHERE id = ?",
        (subscription_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None
