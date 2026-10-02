"""Rules for budgets: what each category costs per month and how it compares to its budget."""
from budgets import repository
from subscriptions import service as subscriptions_service

NEAR_LIMIT_PERCENT = 80  # from 80% of a budget, the category is shown as "close to the limit"
MAX_BUDGET_CENTS = 1000000  # 10,000 euros


def parse_amount(text):
    """Turn an amount typed by the user, like "25" or "12,50", into cents (2500)."""
    cleaned = text.strip().replace(",", ".")
    return round(float(cleaned) * 100)


def validate_budget(form):
    """Check the "set a budget" form. Return (category, cents, errors)."""
    errors = []

    category = form.get("category", "")
    if category not in subscriptions_service.CATEGORIES:
        errors.append("Choose a category from the list.")

    cents = None
    try:
        cents = parse_amount(form.get("amount", ""))
        if cents <= 0 or cents > MAX_BUDGET_CENTS:
            errors.append("Budget must be between 0.01 and 10,000.")
    except (ValueError, OverflowError):
        errors.append("Budget must be a number, like 25 or 12.50.")

    return category, cents, errors


def set_budget(user_id, form):
    """Validate the form and save the budget. Return the errors."""
    category, cents, errors = validate_budget(form)
    if errors:
        return errors
    repository.set_budget(user_id, category, cents)
    return []


def remove_budget(user_id, category):
    """Remove the budget for one category."""
    repository.remove_budget(user_id, category)


def spending_by_category(subscriptions):
    """Add up what the subscriptions cost per category. Return {category: totals}."""
    spending = {}
    for sub in subscriptions:
        category = sub["category"]
        if category not in spending:
            spending[category] = {"monthly_cents": 0, "yearly_cents": 0, "count": 0}
        spending[category]["monthly_cents"] += sub["monthly_cost_cents"]
        spending[category]["yearly_cents"] += sub["yearly_cost_cents"]
        spending[category]["count"] += 1
    return spending


def percent(part, whole):
    """part as a whole-number percentage of whole, e.g. percent(1, 4) is 25. 0 if whole is 0."""
    if whole == 0:
        return 0
    return round(part * 100 / whole)


def monthly_cost(row):
    """Sort key: the monthly cost of a report row."""
    return row["monthly_cents"]


def budget_status(spent_cents, budget_cents):
    """'none' without a budget, then 'over', 'near' (80% or more) or 'ok'."""
    if budget_cents is None:
        return "none"
    if spent_cents > budget_cents:
        return "over"
    if spent_cents * 100 >= budget_cents * NEAR_LIMIT_PERCENT:
        return "near"
    return "ok"


def build_report(subscriptions, budgets):
    """One row per category that has spending or a budget, most expensive first.

    Each row says what the category costs, its budget, how much of the budget
    is used and its status, so the page only has to show the numbers.
    """
    spending = spending_by_category(subscriptions)
    total_monthly = 0
    for totals in spending.values():
        total_monthly += totals["monthly_cents"]

    rows = []
    for category in subscriptions_service.CATEGORIES:
        if category not in spending and category not in budgets:
            continue
        totals = spending.get(category, {"monthly_cents": 0, "yearly_cents": 0, "count": 0})
        budget = budgets.get(category)
        row = {
            "category": category,
            "count": totals["count"],
            "monthly_cents": totals["monthly_cents"],
            "yearly_cents": totals["yearly_cents"],
            "share_percent": percent(totals["monthly_cents"], total_monthly),
            "budget_cents": budget,
            "used_percent": percent(totals["monthly_cents"], budget) if budget else None,
            "status": budget_status(totals["monthly_cents"], budget),
        }
        rows.append(row)
    rows.sort(key=monthly_cost, reverse=True)
    return rows


def summarise_report(rows):
    """Totals for the cards at the top of the budgets page."""
    monthly_total = 0
    yearly_total = 0
    budget_total = 0
    over_budget = []
    for row in rows:
        monthly_total += row["monthly_cents"]
        yearly_total += row["yearly_cents"]
        if row["budget_cents"] is not None:
            budget_total += row["budget_cents"]
        if row["status"] == "over":
            over_budget.append(row["category"])
    return {
        "monthly_total_cents": monthly_total,
        "yearly_total_cents": yearly_total,
        "budget_total_cents": budget_total,
        "over_budget": over_budget,
    }


def get_budget_report(user_id, today):
    """The budgets page for one user.

    Subscription data comes ONLY from get_active_subscriptions(), the one
    function the Subscriptions domain shares (see ADR-2).
    """
    subscriptions = subscriptions_service.get_active_subscriptions(user_id, today)
    budgets = repository.list_budgets(user_id)
    return build_report(subscriptions, budgets)
