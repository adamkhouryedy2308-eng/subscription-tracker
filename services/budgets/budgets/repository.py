"""SQL for the budgets table. Only this file reads or writes that table."""
import db

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    monthly_limit_cents INTEGER NOT NULL CHECK (monthly_limit_cents > 0),
    UNIQUE (user_id, category)
)
"""


def set_budget(user_id, category, monthly_limit_cents):
    """Save this user's budget for a category, replacing the old one if there is one."""
    conn = db.get_connection()
    conn.execute(
        """
        INSERT INTO budgets (user_id, category, monthly_limit_cents)
        VALUES (?, ?, ?)
        ON CONFLICT (user_id, category)
        DO UPDATE SET monthly_limit_cents = excluded.monthly_limit_cents
        """,
        (user_id, category, monthly_limit_cents),
    )
    conn.commit()
    conn.close()


def remove_budget(user_id, category):
    """Delete this user's budget for a category."""
    conn = db.get_connection()
    conn.execute(
        "DELETE FROM budgets WHERE user_id = ? AND category = ?",
        (user_id, category),
    )
    conn.commit()
    conn.close()


def list_budgets(user_id):
    """Return this user's budgets as {category: monthly limit in cents}."""
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT category, monthly_limit_cents FROM budgets WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    conn.close()
    budgets = {}
    for row in rows:
        budgets[row["category"]] = row["monthly_limit_cents"]
    return budgets
