NETFLIX = {
    "name": "Netflix",
    "category": "Entertainment",
    "price": "13.49",
    "billing_cycle": "monthly",
    "first_payment_date": "2026-01-15",
}


def test_home_sends_you_to_the_subscriptions_list(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/subscriptions/")


def test_empty_list_invites_you_to_add_one(client):
    response = client.get("/subscriptions/")
    assert response.status_code == 200
    assert "No subscriptions yet" in response.get_data(as_text=True)


def test_add_page_shows_the_form(client):
    response = client.get("/subscriptions/new")
    assert response.status_code == 200
    assert "Add a subscription" in response.get_data(as_text=True)


def test_adding_a_valid_subscription_shows_it_in_the_list(client):
    response = client.post("/subscriptions/new", data=NETFLIX)
    assert response.status_code == 302
    assert "added=Netflix" in response.headers["Location"]

    page = client.get("/subscriptions/").get_data(as_text=True)
    assert "Netflix" in page
    assert "€13.49" in page


def test_list_confirms_what_was_just_added(client):
    page = client.get("/subscriptions/?added=Netflix").get_data(as_text=True)
    assert "was added to your subscriptions" in page


def test_adding_an_invalid_subscription_shows_the_errors(client):
    form = dict(NETFLIX)
    form["price"] = "abc"
    response = client.post("/subscriptions/new", data=form)
    page = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "Price must be a number, like 9.99." in page
    assert 'value="Netflix"' in page
