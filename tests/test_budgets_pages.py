from tests.test_subscriptions_pages import NETFLIX

BEN = {"email": "ben@example.com", "password": "other-pass", "confirm_password": "other-pass"}


def test_visitors_are_sent_to_log_in(guest):
    assert guest.get("/budgets/").headers["Location"].endswith("/login")


def test_empty_budgets_page_explains_what_to_do(client):
    response = client.get("/budgets/")
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Nothing to add up yet" in page
    assert "Set a monthly budget" in page


def test_budgets_page_shows_spending_per_category(client):
    client.post("/subscriptions/new", data=NETFLIX)
    page = client.get("/budgets/").get_data(as_text=True)
    assert "Entertainment" in page
    assert "€13.49" in page
    assert "€161.88" in page       # per year
    assert "no budget" in page


def test_saving_a_budget_shows_how_much_is_used(client):
    client.post("/subscriptions/new", data=NETFLIX)
    response = client.post("/budgets/", data={"category": "Entertainment", "amount": "20"})
    assert response.status_code == 302
    assert "saved=Entertainment" in response.headers["Location"]

    page = client.get("/budgets/?saved=Entertainment").get_data(as_text=True)
    assert "Budget for <strong>Entertainment</strong> saved." in page
    assert "67% of €20.00" in page
    assert "€6.51 left" in page


def test_going_over_budget_is_shown(client):
    client.post("/subscriptions/new", data=NETFLIX)
    client.post("/budgets/", data={"category": "Entertainment", "amount": "10"})
    page = client.get("/budgets/").get_data(as_text=True)
    assert "over by €3.49" in page
    assert "stat-alert" in page


def test_saving_a_wrong_budget_shows_the_error(client):
    response = client.post("/budgets/", data={"category": "Music", "amount": "lots"})
    page = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "Budget must be a number, like 25 or 12.50." in page
    assert 'value="lots"' in page


def test_removing_a_budget(client):
    client.post("/budgets/", data={"category": "Music", "amount": "15"})
    response = client.post("/budgets/remove", data={"category": "Music"})
    assert "removed=Music" in response.headers["Location"]
    page = client.get("/budgets/").get_data(as_text=True)
    assert "Nothing to add up yet" in page


def test_remove_only_works_with_post(client):
    assert client.get("/budgets/remove").status_code == 405


def test_other_users_never_see_my_budgets(client):
    client.post("/budgets/", data={"category": "Music", "amount": "15"})
    client.post("/logout")
    client.post("/register", data=BEN)
    page = client.get("/budgets/").get_data(as_text=True)
    assert "Nothing to add up yet" in page
    assert "€15.00" not in page
