from datetime import date

import pytest

from budgets import repository, service

TODAY = date(2026, 10, 2)
USER_ID = 1


def sub(category, monthly_cents, yearly_cents=None):
    """A subscription as get_active_subscriptions() returns it (only the fields budgets use)."""
    if yearly_cents is None:
        yearly_cents = monthly_cents * 12
    return {"category": category, "monthly_cost_cents": monthly_cents, "yearly_cost_cents": yearly_cents}


# --- Checking the budget form ------------------------------------------------------

@pytest.mark.parametrize("text, cents", [("25", 2500), ("12,50", 1250), (" 9.99 ", 999)])
def test_parse_amount_turns_text_into_cents(text, cents):
    assert service.parse_amount(text) == cents


def test_valid_budget_form_has_no_errors():
    category, cents, errors = service.validate_budget({"category": "Music", "amount": "15"})
    assert (category, cents, errors) == ("Music", 1500, [])


@pytest.mark.parametrize("form, error", [
    ({"category": "Cars", "amount": "15"}, "Choose a category from the list."),
    ({"category": "Music", "amount": "abc"}, "Budget must be a number, like 25 or 12.50."),
    ({"category": "Music", "amount": "inf"}, "Budget must be a number, like 25 or 12.50."),
    ({"category": "Music", "amount": "0"}, "Budget must be between 0.01 and 10,000."),
    ({"category": "Music", "amount": "-5"}, "Budget must be between 0.01 and 10,000."),
    ({"category": "Music", "amount": "10000.01"}, "Budget must be between 0.01 and 10,000."),
    ({}, "Choose a category from the list."),
])
def test_invalid_budget_forms_give_a_clear_error(form, error):
    category, cents, errors = service.validate_budget(form)
    assert error in errors


@pytest.mark.parametrize("form, percent", [({}, 80), ({"warn_percent": ""}, 80),
                                           ({"warn_percent": "50"}, 50), ({"warn_percent": 100}, 100)])
def test_warning_level_is_80_unless_the_user_picks_one(form, percent):
    assert service.validate_warn_percent(form) == (percent, [])


@pytest.mark.parametrize("text", ["0", "101", "-5", "12.5", "half"])
def test_invalid_warning_levels_give_a_clear_error(text):
    assert service.validate_warn_percent({"warn_percent": text}) == (
        None, ["Warning level must be a whole number from 1 to 100."])


# --- Saving budgets ----------------------------------------------------------------

def test_set_budget_saves_it_and_saving_again_replaces_it(temp_db):
    assert service.set_budget(USER_ID, {"category": "Music", "amount": "15"}) == []
    assert service.set_budget(USER_ID, {"category": "Music", "amount": "20"}) == []
    assert service.list_budgets(USER_ID) == {"Music": 2000}


def test_set_budget_saves_the_warning_level_too(temp_db):
    service.set_budget(USER_ID, {"category": "Music", "amount": "15", "warn_percent": "50"})
    service.set_budget(USER_ID, {"category": "Education", "amount": "40"})
    assert repository.list_warn_percents(USER_ID) == {"Music": 50, "Education": 80}


def test_a_bad_warning_level_saves_nothing(temp_db):
    errors = service.set_budget(USER_ID, {"category": "Music", "amount": "15", "warn_percent": "500"})
    assert errors == ["Warning level must be a whole number from 1 to 100."]
    assert service.list_budgets(USER_ID) == {}


def test_set_budget_with_errors_saves_nothing(temp_db):
    errors = service.set_budget(USER_ID, {"category": "Music", "amount": "free"})
    assert errors == ["Budget must be a number, like 25 or 12.50."]
    assert service.list_budgets(USER_ID) == {}


def test_remove_budget(temp_db):
    service.set_budget(USER_ID, {"category": "Music", "amount": "15"})
    service.remove_budget(USER_ID, "Music")
    assert service.list_budgets(USER_ID) == {}


# --- The spending calculator --------------------------------------------------------

def test_spending_by_category_adds_up_each_category():
    spending = service.spending_by_category([
        sub("Entertainment", 1349), sub("Music", 1099), sub("Entertainment", 899),
    ])
    assert spending["Entertainment"] == {"monthly_cents": 2248, "yearly_cents": 26976, "count": 2}
    assert spending["Music"]["monthly_cents"] == 1099


@pytest.mark.parametrize("spent, budget, status", [
    (500, None, "none"),
    (500, 1000, "ok"),
    (799, 1000, "ok"),
    (800, 1000, "near"),     # exactly 80% counts as close to the limit
    (1000, 1000, "near"),    # at the limit is not over yet
    (1001, 1000, "over"),
])
def test_budget_status(spent, budget, status):
    assert service.budget_status(spent, budget) == status


@pytest.mark.parametrize("spent, warn_percent, status", [
    (499, 50, "ok"),
    (500, 50, "near"),       # a budget set to warn at 50% is close to the limit sooner
    (899, 90, "ok"),
    (900, 90, "near"),
])
def test_budget_status_uses_the_budgets_own_warning_level(spent, warn_percent, status):
    assert service.budget_status(spent, 1000, warn_percent) == status


def test_report_rows_show_the_warning_level_of_their_budget():
    rows = service.build_report([sub("Music", 600), sub("Entertainment", 3000)],
                                {"Music": 1000}, {"Music": 50})
    entertainment, music = rows
    assert (music["warn_percent"], music["status"]) == (50, "near")   # 60% used, warns at 50%
    assert entertainment["warn_percent"] is None                      # no budget, so no warning level


def test_percent():
    assert service.percent(1, 4) == 25
    assert service.percent(5, 0) == 0


def test_report_has_one_row_per_used_category_most_expensive_first():
    subscriptions = [sub("Music", 1000), sub("Entertainment", 3000)]
    rows = service.build_report(subscriptions, {"Music": 800, "Education": 2000})
    assert [row["category"] for row in rows] == ["Entertainment", "Music", "Education"]

    entertainment, music, education = rows
    assert entertainment["share_percent"] == 75
    assert entertainment["status"] == "none"
    assert entertainment["used_percent"] is None
    assert music["used_percent"] == 125
    assert music["status"] == "over"
    assert education["monthly_cents"] == 0      # a budget with nothing spent yet
    assert education["status"] == "ok"


def test_summarise_report():
    rows = service.build_report([sub("Music", 1000), sub("Entertainment", 3000, 35000)],
                                {"Music": 800, "Education": 2000})
    summary = service.summarise_report(rows)
    assert summary["monthly_total_cents"] == 4000
    assert summary["yearly_total_cents"] == 47000
    assert summary["budget_total_cents"] == 2800
    assert summary["over_budget"] == ["Music"]


def test_summarise_an_empty_report():
    summary = service.summarise_report([])
    assert summary == {"monthly_total_cents": 0, "yearly_total_cents": 0,
                       "budget_total_cents": 0, "over_budget": []}


# --- The report for one user ----------------------------------------------------------

def test_report_uses_the_users_own_budgets(temp_db):
    subscriptions = [sub("Entertainment", 1349)]
    service.set_budget(USER_ID, {"category": "Entertainment", "amount": "10"})

    rows = service.get_budget_report(USER_ID, subscriptions)
    assert rows[0]["category"] == "Entertainment"
    assert rows[0]["monthly_cents"] == 1349
    assert rows[0]["status"] == "over"

    other_user = 2
    assert service.get_budget_report(other_user, subscriptions)[0]["status"] == "none"
