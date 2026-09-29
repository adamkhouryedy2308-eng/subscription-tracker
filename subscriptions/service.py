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


def create_subscription(form, today):
    """Validate a form and save it. Return (new_id, errors)."""
    clean_data, errors = validate(form, today)
    if errors:
        return None, errors
    return repository.add_subscription(clean_data), []


def get_active_subscriptions(today):
    """The ONE function other domains may call to read subscription data.

    Returns plain dicts with the monthly cost and next payment date worked out,
    so callers never need to know how the subscriptions table looks.
    """
    result = []
    for sub in repository.list_subscriptions("active"):
        first_payment = parse_date(sub["first_payment_date"])
        result.append({
            "id": sub["id"],
            "name": sub["name"],
            "category": sub["category"],
            "price_cents": sub["price_cents"],
            "billing_cycle": sub["billing_cycle"],
            "monthly_cost_cents": monthly_cost_cents(sub["price_cents"], sub["billing_cycle"]),
            "next_payment_date": next_payment_date(first_payment, sub["billing_cycle"], today),
            "is_trial": bool(sub["is_trial"]),
            "last_used_date": sub["last_used_date"],
        })
    return result
