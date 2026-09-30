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


def add_netflix(client):
    """Add Netflix through the form and return the id it got (the first row is 1)."""
    client.post("/subscriptions/new", data=NETFLIX)
    return 1


def test_edit_page_starts_filled_in(client):
    sub_id = add_netflix(client)
    page = client.get(f"/subscriptions/{sub_id}/edit").get_data(as_text=True)
    assert "Edit Netflix" in page
    assert 'value="Netflix"' in page
    assert 'value="13.49"' in page


def test_editing_saves_the_new_price(client):
    sub_id = add_netflix(client)
    form = dict(NETFLIX)
    form["price"] = "15.99"
    response = client.post(f"/subscriptions/{sub_id}/edit", data=form)
    assert response.status_code == 302
    assert "updated=Netflix" in response.headers["Location"]
    assert "€15.99" in client.get("/subscriptions/").get_data(as_text=True)


def test_editing_with_a_mistake_shows_the_errors(client):
    sub_id = add_netflix(client)
    form = dict(NETFLIX)
    form["billing_cycle"] = "daily"
    response = client.post(f"/subscriptions/{sub_id}/edit", data=form)
    assert response.status_code == 400
    assert "Choose a billing cycle." in response.get_data(as_text=True)


def test_editing_a_missing_subscription_is_not_found(client):
    assert client.get("/subscriptions/99/edit").status_code == 404


def test_cancelling_moves_it_to_the_cancelled_section(client):
    sub_id = add_netflix(client)
    response = client.post(f"/subscriptions/{sub_id}/cancel")
    assert response.status_code == 302
    assert "cancelled=Netflix" in response.headers["Location"]

    page = client.get("/subscriptions/").get_data(as_text=True)
    assert "No subscriptions yet" in page
    assert "Cancelled" in page
    assert "€161.88" in page


def test_cancel_only_works_with_post(client):
    sub_id = add_netflix(client)
    assert client.get(f"/subscriptions/{sub_id}/cancel").status_code == 405


def test_a_cancelled_subscription_cannot_be_edited(client):
    sub_id = add_netflix(client)
    client.post(f"/subscriptions/{sub_id}/cancel")
    assert client.get(f"/subscriptions/{sub_id}/edit").status_code == 404


def test_cancelling_a_missing_subscription_is_not_found(client):
    assert client.post("/subscriptions/99/cancel").status_code == 404
