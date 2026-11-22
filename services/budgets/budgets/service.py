"""Rules for budgets: what each category costs per month and how it compares to its budget."""
from budgets import repository

# The same 10 categories as the Subscriptions service. Copied on purpose: Budgets
# must keep working (saving and checking budgets) even when Subscriptions is down.
CATEGORIES = [
    "Entertainment",
    "Music",
    "AI Tools",
    "Health & Fitness",
    "Cloud & Software",
    "News & Magazines",
    "Education",
    "Food & Delivery",
    "Phone & Internet",
    "Other",
]

NEAR_LIMIT_PERCENT = 80  # the usual warning level: from 80% of a budget, "close to the limit"
MAX_BUDGET_CENTS = 1000000  # 10,000 euros


def parse_amount(text):
    """Turn an amount typed by the user, like "25" or "12,50", into cents (2500)."""
    cleaned = text.strip().replace(",", ".")
    return round(float(cleaned) * 100)


def validate_budget(form):
    """Check the "set a budget" form. Return (category, cents, errors)."""
    errors = []

    category = form.get("category", "")
    if category not in CATEGORIES:
        errors.append("Choose a category from the list.")

    cents = None
    try:
        cents = parse_amount(form.get("amount", ""))
        if cents <= 0 or cents > MAX_BUDGET_CENTS:
            errors.append("Budget must be between 0.01 and 10,000.")
    except (ValueError, OverflowError):
        errors.append("Budget must be a number, like 25 or 12.50.")

    return category, cents, errors


def validate_warn_percent(form):
    """Check the "warn me at" field. Empty or missing means the usual 80%. Return (percent, errors)."""
    text = str(form.get("warn_percent", "")).strip()
    if text == "":
        return NEAR_LIMIT_PERCENT, []
    if not text.isdigit() or not 1 <= int(text) <= 100:
        return None, ["Warning level must be a whole number from 1 to 100."]
    return int(text), []


def set_budget(user_id, form):
    """Validate the form and save the budget with its warning level. Return the errors."""
    category, cents, errors = validate_budget(form)
    warn_percent, warn_errors = validate_warn_percent(form)
    errors += warn_errors
    if errors:
        return errors
    repository.set_budget(user_id, category, cents, warn_percent)
    return []


def remove_budget(user_id, category):
    """Remove the budget for one category."""
    repository.remove_budget(user_id, category)


def list_budgets(user_id):
    """This user's budgets as {category: monthly limit in cents}. Needs no subscription data."""
    return repository.list_budgets(user_id)


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


def budget_status(spent_cents, budget_cents, warn_percent=NEAR_LIMIT_PERCENT):
    """'none' without a budget, then 'over', 'near' (warn_percent or more, 80% unless set) or 'ok'."""
    if budget_cents is None:
        return "none"
    if spent_cents > budget_cents:
        return "over"
    if spent_cents * 100 >= budget_cents * warn_percent:
        return "near"
    return "ok"


def build_report(subscriptions, budgets, warn_percents=None):
    """One row per category that has spending or a budget, most expensive first.

    Each row says what the category costs, its budget, how much of the budget
    is used, at what percentage it warns and its status, so the page only has to
    show the numbers. warn_percents is {category: percent}; a missing one means 80%.
    """
    if warn_percents is None:
        warn_percents = {}
    spending = spending_by_category(subscriptions)
    total_monthly = 0
    for totals in spending.values():
        total_monthly += totals["monthly_cents"]

    rows = []
    for category in CATEGORIES:
        if category not in spending and category not in budgets:
            continue
        totals = spending.get(category, {"monthly_cents": 0, "yearly_cents": 0, "count": 0})
        budget = budgets.get(category)
        warn_percent = warn_percents.get(category, NEAR_LIMIT_PERCENT)
        row = {
            "category": category,
            "count": totals["count"],
            "monthly_cents": totals["monthly_cents"],
            "yearly_cents": totals["yearly_cents"],
            "share_percent": percent(totals["monthly_cents"], total_monthly),
            "budget_cents": budget,
            "used_percent": percent(totals["monthly_cents"], budget) if budget else None,
            "warn_percent": warn_percent if budget else None,
            "status": budget_status(totals["monthly_cents"], budget, warn_percent),
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


def get_budget_report(user_id, subscriptions):
    """The budgets page for one user.

    The subscriptions come from the Subscriptions service over HTTP
    (subscriptions_client.py), the one way in across the seam (ADR-2, ADR-6).
    """
    budgets = repository.list_budgets(user_id)
    return build_report(subscriptions, budgets, repository.list_warn_percents(user_id))
