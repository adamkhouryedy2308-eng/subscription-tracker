import os
from datetime import date

import pytest

from subscriptions import bank_import

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "sample_data", "bank_statement_example.csv")


def payments(description, dates, amounts):
    """Payments with the same description on the given dates and amounts (in cents)."""
    result = []
    for when, cents in zip(dates, amounts):
        result.append({"date": when, "description": description, "amount_cents": cents})
    return result


# --- Reading the file -------------------------------------------------------------

def test_read_statement_keeps_only_money_going_out():
    text = "Date,Description,Amount\n2026-09-15,NETFLIX.COM,-13.49\n2026-09-28,SALARY,1200.00\n"
    found, skipped = bank_import.read_statement(text)
    assert found == [{"date": date(2026, 9, 15), "description": "NETFLIX.COM", "amount_cents": 1349}]
    assert skipped == 0


def test_read_statement_accepts_european_dates_commas_and_any_column_case():
    text = " date ,DESCRIPTION,Amount\n15/09/2026,Spotify,\"-10,99\"\n"
    found, skipped = bank_import.read_statement(text)
    assert found[0]["date"] == date(2026, 9, 15)
    assert found[0]["amount_cents"] == 1099


def test_rows_that_cannot_be_read_are_counted_and_skipped():
    text = "Date,Description,Amount\nyesterday,Netflix,-13.49\n2026-09-15,Netflix,lots\n2026-09-16,Spotify\n"
    found, skipped = bank_import.read_statement(text)
    assert found == []
    assert skipped == 3


def test_a_file_without_the_right_columns_is_refused():
    with pytest.raises(ValueError, match="Date, Description and Amount"):
        bank_import.read_statement("When,What,How much\n2026-09-15,Netflix,-13.49\n")
    with pytest.raises(ValueError):
        bank_import.read_statement("")


# --- Recognising companies ---------------------------------------------------------

def test_normalise_name_keeps_only_letters():
    assert bank_import.normalise_name("NETFLIX.COM 4471") == "netflix com"
    assert bank_import.normalise_name("Netflix.com 9012") == "netflix com"


def test_identify_known_services_and_others():
    assert bank_import.identify("openai chatgpt subscr") == ("ChatGPT Plus", "AI Tools")
    assert bank_import.identify("padel club madrid") == ("Padel Club Madrid", "Other")


# --- Recognising a rhythm and a price ------------------------------------------------

@pytest.mark.parametrize("dates, cycle", [
    ([date(2026, 9, 1), date(2026, 9, 8), date(2026, 9, 15)], "weekly"),
    ([date(2026, 7, 15), date(2026, 8, 17), date(2026, 9, 15)], "monthly"),     # 33 and 29 days
    ([date(2026, 1, 10), date(2026, 4, 12), date(2026, 7, 11)], "quarterly"),
    ([date(2024, 5, 10), date(2025, 5, 10), date(2026, 5, 11)], "yearly"),
    ([date(2026, 7, 1), date(2026, 7, 20), date(2026, 9, 2)], None),           # no regular rhythm
])
def test_detect_cycle(dates, cycle):
    assert bank_import.detect_cycle(dates) == cycle


def test_similar_amounts_allows_a_small_price_rise_only():
    assert bank_import.similar_amounts([1099, 1099, 1199]) is True
    assert bank_import.similar_amounts([4217, 1890, 6305]) is False


# --- Finding subscriptions --------------------------------------------------------------

def test_a_monthly_payment_seen_three_times_is_suggested():
    found = payments("NETFLIX.COM 4471", [date(2026, 7, 15), date(2026, 8, 17), date(2026, 9, 15)], [1349] * 3)
    [suggestion] = bank_import.find_recurring(found, [])
    assert suggestion == {
        "name": "Netflix", "category": "Entertainment", "amount_cents": 1349,
        "billing_cycle": "monthly", "count": 3, "last_payment_date": date(2026, 9, 15),
        "bank_text": "NETFLIX.COM 4471", "already_tracked": False,
    }


def test_two_payments_are_not_enough():
    found = payments("NETFLIX.COM", [date(2026, 8, 15), date(2026, 9, 15)], [1349] * 2)
    assert bank_import.find_recurring(found, []) == []


def test_a_subscription_already_in_the_list_is_marked():
    found = payments("NETFLIX.COM", [date(2026, 7, 15), date(2026, 8, 15), date(2026, 9, 15)], [1349] * 3)
    [suggestion] = bank_import.find_recurring(found, ["Netflix", "Spotify"])
    assert suggestion["already_tracked"] is True


def test_the_sample_statement_finds_exactly_the_six_subscriptions():
    with open(SAMPLE) as file:
        found, skipped = bank_import.read_statement(file.read())
    suggestions = bank_import.find_recurring(found, [])
    summary = [(s["name"], s["billing_cycle"], s["amount_cents"]) for s in suggestions]
    assert summary == [
        ("Basic-Fit", "monthly", 2999),
        ("ChatGPT Plus", "monthly", 2000),
        ("iCloud+", "monthly", 299),
        ("Netflix", "monthly", 1349),
        ("Padel Club Madrid", "weekly", 800),
        ("Spotify", "monthly", 1199),       # the latest price after the rise from 10.99
    ]
    assert skipped == 0
