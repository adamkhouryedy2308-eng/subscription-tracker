"""Business rules for subscriptions: checking input and working out costs and dates."""
import calendar
from datetime import date, timedelta

from subscriptions import repository

# How many times each billing cycle charges in one year.
CYCLES_PER_YEAR = {"weekly": 52, "monthly": 12, "quarterly": 4, "yearly": 1}

# A fixed list keeps categories consistent, so budgets can match them exactly.
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

MAX_NAME_LENGTH = 100
MAX_PRICE_CENTS = 1000000  # 10,000 euros: anything above is almost surely a typo


def parse_price(text):
    """Turn a price typed by the user, like "9.99" or "9,99", into cents (999)."""
    cleaned = text.strip().replace(",", ".")
    return round(float(cleaned) * 100)


def parse_date(text):
    """Turn "2026-09-29" into a date object (raises ValueError if invalid)."""
    return date.fromisoformat(text.strip())


def validate(form, today):
    """Check a submitted form. Return (clean_data, errors); errors is empty if valid."""
    errors = []

    name = form.get("name", "").strip()
    if not name:
        errors.append("Name is required.")
    elif len(name) > MAX_NAME_LENGTH:
        errors.append(f"Name must be at most {MAX_NAME_LENGTH} characters.")

    category = form.get("category", "")
    if category not in CATEGORIES:
        errors.append("Choose a category from the list.")

    price_cents = None
    try:
        price_cents = parse_price(form.get("price", ""))
        if price_cents < 0 or price_cents > MAX_PRICE_CENTS:
            errors.append("Price must be between 0 and 10,000.")
    except (ValueError, OverflowError):
        errors.append("Price must be a number, like 9.99.")

    billing_cycle = form.get("billing_cycle", "")
    if billing_cycle not in CYCLES_PER_YEAR:
        errors.append("Choose a billing cycle.")

    first_payment_date = None
    try:
        first_payment_date = parse_date(form.get("first_payment_date", ""))
    except ValueError:
        errors.append("First payment date must be a valid date.")

    last_used_date = None
    if form.get("last_used_date", "").strip():
        try:
            last_used_date = parse_date(form["last_used_date"])
            if last_used_date > today:
                errors.append("Last used date cannot be in the future.")
        except ValueError:
            errors.append("Last used date must be a valid date.")

    clean_data = {
        "name": name,
        "category": category,
        "price_cents": price_cents,
        "billing_cycle": billing_cycle,
        "first_payment_date": first_payment_date.isoformat() if first_payment_date else None,
        "is_trial": 1 if form.get("is_trial") == "on" else 0,
        "last_used_date": last_used_date.isoformat() if last_used_date else None,
    }
    return clean_data, errors


def monthly_cost_cents(price_cents, billing_cycle):
    """What a subscription costs per month, whatever its billing cycle."""
    return round(price_cents * CYCLES_PER_YEAR[billing_cycle] / 12)


def yearly_cost_cents(price_cents, billing_cycle):
    """What a subscription costs per year."""
    return price_cents * CYCLES_PER_YEAR[billing_cycle]


def add_months(start, months):
    """Move a date forward by whole months, clamping to the month's last day.

    Example: 31 January + 1 month = 28 February (or 29 in a leap year).
    """
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(start.day, last_day))


def nth_payment_date(first_payment, billing_cycle, n):
    """The date of payment number n (payment 0 is the first payment)."""
    if billing_cycle == "weekly":
        return first_payment + timedelta(weeks=n)
    months_between_payments = 12 // CYCLES_PER_YEAR[billing_cycle]
    return add_months(first_payment, n * months_between_payments)


def next_payment_date(first_payment, billing_cycle, today):
    """The first payment that falls on today or later."""
    n = 0
    payment = first_payment
    while payment < today:
        n += 1
        payment = nth_payment_date(first_payment, billing_cycle, n)
    return payment


def create_subscription(user_id, form, today):
    """Validate a form and save it for this user. Return (new_id, errors)."""
    clean_data, errors = validate(form, today)
    if errors:
        return None, errors
    return repository.add_subscription(user_id, clean_data), []


def get_subscription(user_id, subscription_id):
    """One of this user's subscriptions as saved, or None if it is not theirs or does not exist."""
    return repository.get_subscription(user_id, subscription_id)


def subscription_to_form(sub):
    """Turn a saved subscription back into form values, so the edit form starts filled in."""
    return {
        "name": sub["name"],
        "category": sub["category"],
        "price": f"{sub['price_cents'] / 100:.2f}",
        "billing_cycle": sub["billing_cycle"],
        "first_payment_date": sub["first_payment_date"],
        "is_trial": "on" if sub["is_trial"] else "",
        "last_used_date": sub["last_used_date"] or "",
    }


def update_subscription(user_id, subscription_id, form, today):
    """Validate a form and save it over one of this user's subscriptions. Return the errors.

    If the price is different from before, the change is also saved in the price history.
    """
    clean_data, errors = validate(form, today)
    if errors:
        return errors
    old = repository.get_subscription(user_id, subscription_id)
    if old is None:
        return []
    repository.update_subscription(user_id, subscription_id, clean_data)
    if clean_data["price_cents"] != old["price_cents"]:
        repository.add_price_change(subscription_id, old["price_cents"],
                                    clean_data["price_cents"], today.isoformat())
    return []


def get_price_history(user_id, subscription_id):
    """The price changes of one of this user's subscriptions, oldest first ([] if it is not theirs)."""
    if repository.get_subscription(user_id, subscription_id) is None:
        return []
    history = []
    for change in repository.list_price_changes(subscription_id):
        history.append({
            "old_price_cents": change["old_price_cents"],
            "new_price_cents": change["new_price_cents"],
            "changed_date": parse_date(change["changed_date"]),
        })
    return history


def percent_change(old_cents, new_cents):
    """How much a price changed, in whole percent: 1000 to 1250 is 25, 1000 to 900 is -10."""
    if old_cents == 0:
        return 0
    return round((new_cents - old_cents) * 100 / old_cents)


def cancel_subscription(user_id, subscription_id, today):
    """Cancel a subscription today. It moves to the cancelled list instead of being deleted."""
    repository.cancel_subscription(user_id, subscription_id, today.isoformat())


def get_cancelled_subscriptions(user_id):
    """This user's cancelled subscriptions, with what cancelling each one saves per year."""
    result = []
    for sub in repository.list_subscriptions(user_id, "cancelled"):
        result.append({
            "id": sub["id"],
            "name": sub["name"],
            "category": sub["category"],
            "cancelled_date": parse_date(sub["cancelled_date"]),
            "yearly_saving_cents": yearly_cost_cents(sub["price_cents"], sub["billing_cycle"]),
        })
    return result


def yearly_savings_cents(cancelled):
    """How much the user saves per year thanks to everything they cancelled."""
    total = 0
    for sub in cancelled:
        total += sub["yearly_saving_cents"]
    return total


def get_active_subscriptions(user_id, today):
    """The ONE function other domains may call to read subscription data.

    Returns this user's subscriptions as plain dicts with the monthly cost and
    next payment date worked out, so callers never need to know how the
    subscriptions table looks.
    """
    result = []
    for sub in repository.list_subscriptions(user_id, "active"):
        first_payment = parse_date(sub["first_payment_date"])
        next_payment = next_payment_date(first_payment, sub["billing_cycle"], today)
        history = get_price_history(user_id, sub["id"])
        original_price = history[0]["old_price_cents"] if history else sub["price_cents"]
        result.append({
            "id": sub["id"],
            "name": sub["name"],
            "category": sub["category"],
            "price_cents": sub["price_cents"],
            "billing_cycle": sub["billing_cycle"],
            "monthly_cost_cents": monthly_cost_cents(sub["price_cents"], sub["billing_cycle"]),
            "yearly_cost_cents": yearly_cost_cents(sub["price_cents"], sub["billing_cycle"]),
            "first_payment_date": first_payment,
            "next_payment_date": next_payment,
            "days_until_payment": (next_payment - today).days,
            "is_trial": bool(sub["is_trial"]),
            "last_used_date": sub["last_used_date"],
            "original_price_cents": original_price,
            "price_change_percent": percent_change(original_price, sub["price_cents"]),
            "last_price_change": history[-1] if history else None,
        })
    return result


def summarise(subscriptions):
    """Totals shown at the top of the list page, plus the payment that comes first."""
    monthly_total = 0
    yearly_total = 0
    next_up = None
    for sub in subscriptions:
        monthly_total += sub["monthly_cost_cents"]
        yearly_total += sub["yearly_cost_cents"]
        if next_up is None or sub["next_payment_date"] < next_up["next_payment_date"]:
            next_up = sub
    return {
        "count": len(subscriptions),
        "monthly_total_cents": monthly_total,
        "yearly_total_cents": yearly_total,
        "next_up": next_up,
    }
