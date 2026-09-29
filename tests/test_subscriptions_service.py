from datetime import date

import pytest

from subscriptions import service

TODAY = date(2026, 9, 29)


def valid_form():
    """A form that passes validation; tests change one field at a time."""
    return {
        "name": "Netflix",
        "category": "Entertainment",
        "price": "13.49",
        "billing_cycle": "monthly",
        "first_payment_date": "2026-01-15",
        "last_used_date": "2026-09-20",
    }


# --- Money -------------------------------------------------------------------

@pytest.mark.parametrize("text, cents", [("9.99", 999), ("9,99", 999), (" 10 ", 1000), ("0", 0)])
def test_parse_price_turns_text_into_cents(text, cents):
    assert service.parse_price(text) == cents


@pytest.mark.parametrize("cycle, expected", [
    ("weekly", 4333),     # 10.00 * 52 / 12
    ("monthly", 1000),
    ("quarterly", 333),   # 10.00 / 3
    ("yearly", 83),       # 10.00 / 12
])
def test_monthly_cost_for_every_billing_cycle(cycle, expected):
    assert service.monthly_cost_cents(1000, cycle) == expected


def test_yearly_cost():
    assert service.yearly_cost_cents(999, "monthly") == 11988


# --- Validation --------------------------------------------------------------

def test_valid_form_has_no_errors():
    data, errors = service.validate(valid_form(), TODAY)
    assert errors == []
    assert data["price_cents"] == 1349
    assert data["first_payment_date"] == "2026-01-15"
    assert data["is_trial"] == 0


def test_trial_checkbox_is_stored_as_1():
    form = valid_form()
    form["is_trial"] = "on"
    data, errors = service.validate(form, TODAY)
    assert errors == []
    assert data["is_trial"] == 1


@pytest.mark.parametrize("changes, message", [
    ({"name": "  "}, "Name is required."),
    ({"name": "x" * 101}, "Name must be at most 100 characters."),
    ({"category": "Streaming"}, "Choose a category from the list."),
    ({"price": "abc"}, "Price must be a number, like 9.99."),
    ({"price": "inf"}, "Price must be a number, like 9.99."),
    ({"price": "-5"}, "Price must be between 0 and 10,000."),
    ({"billing_cycle": "daily"}, "Choose a billing cycle."),
    ({"first_payment_date": "31/12/2026"}, "First payment date must be a valid date."),
    ({"last_used_date": "2026-12-01"}, "Last used date cannot be in the future."),
    ({"last_used_date": "not a date"}, "Last used date must be a valid date."),
])
def test_invalid_input_gives_a_clear_error(changes, message):
    form = valid_form()
    form.update(changes)
    data, errors = service.validate(form, TODAY)
    assert message in errors


def test_last_used_date_is_optional():
    form = valid_form()
    form["last_used_date"] = ""
    data, errors = service.validate(form, TODAY)
    assert errors == []
    assert data["last_used_date"] is None


# --- Dates -------------------------------------------------------------------

@pytest.mark.parametrize("start, months, expected", [
    (date(2026, 1, 15), 1, date(2026, 2, 15)),
    (date(2027, 1, 31), 1, date(2027, 2, 28)),   # February is shorter
    (date(2028, 1, 31), 1, date(2028, 2, 29)),   # leap year
    (date(2026, 11, 30), 3, date(2027, 2, 28)),  # crosses into the next year
])
def test_add_months_clamps_to_the_last_day(start, months, expected):
    assert service.add_months(start, months) == expected


@pytest.mark.parametrize("first, cycle, expected", [
    (date(2026, 1, 15), "monthly", date(2026, 10, 15)),
    (date(2026, 9, 29), "monthly", date(2026, 9, 29)),   # due today counts
    (date(2026, 9, 1), "weekly", date(2026, 9, 29)),
    (date(2026, 8, 1), "quarterly", date(2026, 11, 1)),
    (date(2025, 3, 10), "yearly", date(2027, 3, 10)),
    (date(2026, 12, 1), "monthly", date(2026, 12, 1)),   # first payment still ahead
])
def test_next_payment_date(first, cycle, expected):
    assert service.next_payment_date(first, cycle, TODAY) == expected


def test_monthly_payments_keep_the_31st_after_a_short_month():
    # 31 Jan -> 28 Feb -> 31 Mar: each payment is counted from the first one,
    # so a short February does not pull every later payment back to the 28th.
    assert service.next_payment_date(date(2027, 1, 31), "monthly", date(2027, 3, 1)) == date(2027, 3, 31)


# --- Saving and the public function for other domains -------------------------

def test_create_subscription_saves_a_valid_form(temp_db):
    new_id, errors = service.create_subscription(valid_form(), TODAY)
    assert errors == []
    assert new_id is not None


def test_create_subscription_saves_nothing_when_invalid(temp_db):
    form = valid_form()
    form["price"] = "abc"
    new_id, errors = service.create_subscription(form, TODAY)
    assert new_id is None
    assert errors
    assert service.get_active_subscriptions(TODAY) == []


def test_get_active_subscriptions_works_out_cost_and_next_payment(temp_db):
    form = valid_form()
    form["billing_cycle"] = "yearly"
    form["price"] = "120"
    service.create_subscription(form, TODAY)
    subs = service.get_active_subscriptions(TODAY)
    assert len(subs) == 1
    sub = subs[0]
    assert sub["name"] == "Netflix"
    assert sub["monthly_cost_cents"] == 1000
    assert sub["next_payment_date"] == date(2027, 1, 15)
    assert sub["is_trial"] is False
