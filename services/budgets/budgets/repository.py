"""SQL for the budgets table. Only this file reads or writes that table (created in migrations/001_init.sql,
warn_percent added in 003_budget_warn_percent.sql)."""
import db


def set_budget(user_id, category, monthly_limit_cents, warn_percent):
    """Save this user's budget for a category, replacing the old one if there is one.

    First try to change an existing budget; if no row was changed (@@ROWCOUNT = 0),
    this category has no budget yet, so add one. warn_percent was added by migration 003.
    """
    db.execute(
        """
        UPDATE budgets SET monthly_limit_cents = %s, warn_percent = %s
            WHERE user_id = %s AND category = %s;
        IF @@ROWCOUNT = 0
            INSERT INTO budgets (user_id, category, monthly_limit_cents, warn_percent)
                VALUES (%s, %s, %s, %s);
        """,
        (monthly_limit_cents, warn_percent, user_id, category,
         user_id, category, monthly_limit_cents, warn_percent),
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


def list_warn_percents(user_id):
    """Return at what percentage each of this user's budgets warns, as {category: percent}."""
    rows = db.query("SELECT category, warn_percent FROM budgets WHERE user_id = %s", (user_id,))
    warn_percents = {}
    for row in rows:
        warn_percents[row["category"]] = row["warn_percent"]
    return warn_percents
