"""SQL for the budgets table. Only this file reads or writes that table (created in migrations/001_init.sql)."""
import db


def set_budget(user_id, category, monthly_limit_cents):
    """Save this user's budget for a category, replacing the old one if there is one.

    First try to change an existing budget; if no row was changed (@@ROWCOUNT = 0),
    this category has no budget yet, so add one.
    """
    db.execute(
        """
        UPDATE budgets SET monthly_limit_cents = %s WHERE user_id = %s AND category = %s;
        IF @@ROWCOUNT = 0
            INSERT INTO budgets (user_id, category, monthly_limit_cents) VALUES (%s, %s, %s);
        """,
        (monthly_limit_cents, user_id, category, user_id, category, monthly_limit_cents),
    )


def remove_budget(user_id, category):
    """Delete this user's budget for a category."""
    db.execute("DELETE FROM budgets WHERE user_id = %s AND category = %s", (user_id, category))


def list_budgets(user_id):
    """Return this user's budgets as {category: monthly limit in cents}."""
    rows = db.query("SELECT category, monthly_limit_cents FROM budgets WHERE user_id = %s", (user_id,))
    budgets = {}
    for row in rows:
        budgets[row["category"]] = row["monthly_limit_cents"]
    return budgets
