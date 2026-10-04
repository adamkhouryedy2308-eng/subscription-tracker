"""Bank statement import: read a CSV export and find payments that repeat like a subscription.

The file is read in memory and never saved; only the subscriptions the user confirms are stored.
"""
import csv
import io
from datetime import date, datetime

MIN_PAYMENTS = 3                # a payment must appear at least this many times
AMOUNT_TOLERANCE_PERCENT = 20   # amounts may differ this much from the latest one (price rises)

# Days between two payments for each billing cycle, and how many days off it may be
# (months have 28 to 31 days and banks move payments made at the weekend).
CYCLES = {
    "weekly": (7, 1),
    "monthly": (30, 3),
    "quarterly": (91, 7),
    "yearly": (365, 7),
}

# Words that identify well-known services, with a clean name and a category.
KNOWN_SERVICES = {
    "netflix": ("Netflix", "Entertainment"),
    "disney": ("Disney+", "Entertainment"),
    "hbo": ("Max", "Entertainment"),
    "prime video": ("Prime Video", "Entertainment"),
    "spotify": ("Spotify", "Music"),
    "apple music": ("Apple Music", "Music"),
    "openai": ("ChatGPT Plus", "AI Tools"),
    "chatgpt": ("ChatGPT Plus", "AI Tools"),
    "anthropic": ("Claude Pro", "AI Tools"),
    "basic fit": ("Basic-Fit", "Health & Fitness"),
    "icloud": ("iCloud+", "Cloud & Software"),
    "google one": ("Google One", "Cloud & Software"),
    "dropbox": ("Dropbox", "Cloud & Software"),
    "duolingo": ("Duolingo", "Education"),
    "uber eats": ("Uber Eats", "Food & Delivery"),
    "glovo": ("Glovo", "Food & Delivery"),
    "vodafone": ("Vodafone", "Phone & Internet"),
    "movistar": ("Movistar", "Phone & Internet"),
}


def parse_amount(text):
    """Turn "-13.49" or "-13,49" into cents (-1349)."""
    return round(float(text.strip().replace(",", ".")) * 100)


def parse_date(text):
    """Accept "2026-09-15" and "15/09/2026", the two formats banks use most."""
    text = text.strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        return datetime.strptime(text, "%d/%m/%Y").date()


def read_statement(text):
    """Read a bank CSV with the columns Date, Description and Amount.

    Return (payments, skipped_rows). Only money going out (a negative amount)
    is a payment; rows that cannot be read are counted and skipped.
    """
    reader = csv.DictReader(io.StringIO(text))
    columns = [name.strip().lower() for name in reader.fieldnames or []]
    if not {"date", "description", "amount"}.issubset(columns):
        raise ValueError("The file needs the columns Date, Description and Amount.")

    payments = []
    skipped = 0
    for raw_row in reader:
        row = {}
        for key, value in raw_row.items():
            if key is not None:
                row[key.strip().lower()] = value or ""
        try:
            when = parse_date(row["date"])
            cents = parse_amount(row["amount"])
        except (ValueError, OverflowError):
            skipped += 1
            continue
        if cents < 0 and row["description"].strip():
            payments.append({"date": when, "description": row["description"].strip(), "amount_cents": -cents})
    return payments, skipped


def normalise_name(description):
    """Keep only the letters, so "NETFLIX.COM 4471" and "Netflix.com 9012" match: "netflix com"."""
    letters = ""
    for char in description.lower():
        letters += char if char.isalpha() else " "
    return " ".join(letters.split())


def identify(normalised):
    """A clean name and a category: from the known services, otherwise the bank's text and "Other"."""
    for keyword, (name, category) in KNOWN_SERVICES.items():
        if keyword in normalised:
            return name, category
    return normalised.title(), "Other"


def gaps_fit(gaps, days, tolerance):
    """True if every gap between payments is the cycle's length, give or take the tolerance."""
    for gap in gaps:
        if abs(gap - days) > tolerance:
            return False
    return True


def detect_cycle(dates):
    """The billing cycle that matches the gaps between the dates, or None."""
    gaps = []
    for i in range(1, len(dates)):
        gaps.append((dates[i] - dates[i - 1]).days)
    for cycle, (days, tolerance) in CYCLES.items():
        if gaps_fit(gaps, days, tolerance):
            return cycle
    return None


def similar_amounts(amounts):
    """True if every amount is within 20% of the latest one, so a small price rise still matches."""
    latest = amounts[-1]
    for amount in amounts:
        if abs(amount - latest) * 100 > latest * AMOUNT_TOLERANCE_PERCENT:
            return False
    return True


def payment_date(payment):
    """Sort key: the date of a payment."""
    return payment["date"]


def find_recurring(payments, tracked_names):
    """Group payments by company and suggest the groups that repeat like a subscription.

    tracked_names are the subscriptions the user already has, so those are marked
    instead of being suggested twice.
    """
    groups = {}
    for payment in payments:
        key = normalise_name(payment["description"])
        if key not in groups:
            groups[key] = []
        groups[key].append(payment)

    tracked = []
    for name in tracked_names:
        tracked.append(normalise_name(name))

    suggestions = []
    for key, group in groups.items():
        if len(group) < MIN_PAYMENTS:
            continue
        group.sort(key=payment_date)
        dates = [payment["date"] for payment in group]
        amounts = [payment["amount_cents"] for payment in group]
        cycle = detect_cycle(dates)
        if cycle is None or not similar_amounts(amounts):
            continue
        name, category = identify(key)
        suggestions.append({
            "name": name,
            "category": category,
            "amount_cents": amounts[-1],
            "billing_cycle": cycle,
            "count": len(group),
            "last_payment_date": dates[-1],
            "bank_text": group[-1]["description"],
            "already_tracked": normalise_name(name) in tracked,
        })
    suggestions.sort(key=suggestion_name)
    return suggestions


def suggestion_name(suggestion):
    """Sort key: the suggested name."""
    return suggestion["name"].lower()
