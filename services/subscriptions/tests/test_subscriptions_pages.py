"""Integration tests: requests go through Flask, the routes, the service and a real (temporary) database."""
NETFLIX = {
    "name": "Netflix",
    "category": "Entertainment",
    "price": "13.49",
    "billing_cycle": "monthly",
    "first_payment_date": "2026-01-15",
}


def add_netflix(client):
    """Add Netflix and return the id it got."""
    return client.post("/subscriptions", json=NETFLIX).get_json()["id"]


def test_empty_list(client):
    response = client.get("/subscriptions")
    assert response.status_code == 200
    data = response.get_json()
    assert data["subscriptions"] == []
    assert data["summary"]["count"] == 0


def test_options_list_the_categories_and_cycles(client):
    data = client.get("/subscriptions/options").get_json()
    assert len(data["categories"]) == 10
    assert data["billing_cycles"] == ["weekly", "monthly", "quarterly", "yearly"]


def test_adding_a_valid_subscription_shows_it_in_the_list(client):
    response = client.post("/subscriptions", json=NETFLIX)
    assert response.status_code == 201

    data = client.get("/subscriptions").get_json()
    netflix = data["subscriptions"][0]
    assert netflix["name"] == "Netflix"
    assert netflix["price_cents"] == 1349
    assert netflix["first_payment_date"] == "2026-01-15"  # dates travel as text
    assert data["summary"]["monthly_total_cents"] == 1349


def test_adding_an_invalid_subscription_gives_the_errors(client):
    response = client.post("/subscriptions", json=dict(NETFLIX, price="abc"))
    assert response.status_code == 400
    assert "Price must be a number, like 9.99." in response.get_json()["errors"]


def test_a_request_without_a_body_is_refused_with_errors(client):
    response = client.post("/subscriptions")
    assert response.status_code == 400
    assert response.get_json()["errors"]


def test_get_one_gives_the_form_values(client):
    sub_id = add_netflix(client)
    data = client.get(f"/subscriptions/{sub_id}").get_json()
    assert data["form"]["name"] == "Netflix"
    assert data["form"]["price"] == "13.49"
    assert data["history"] == []


def test_editing_saves_the_new_price(client):
    sub_id = add_netflix(client)
    response = client.put(f"/subscriptions/{sub_id}", json=dict(NETFLIX, price="15.99"))
    assert response.status_code == 200
    assert client.get("/subscriptions").get_json()["subscriptions"][0]["price_cents"] == 1599


def test_editing_with_a_mistake_gives_the_errors(client):
    sub_id = add_netflix(client)
    response = client.put(f"/subscriptions/{sub_id}", json=dict(NETFLIX, billing_cycle="daily"))
    assert response.status_code == 400
    assert "Choose a billing cycle." in response.get_json()["errors"]


def test_a_missing_subscription_is_not_found(client):
    assert client.get("/subscriptions/99").status_code == 404
    assert client.put("/subscriptions/99", json=NETFLIX).status_code == 404
    assert client.post("/subscriptions/99/cancel").status_code == 404


def test_cancelling_moves_it_to_the_cancelled_list(client):
    sub_id = add_netflix(client)
    response = client.post(f"/subscriptions/{sub_id}/cancel")
    assert response.status_code == 200
    assert response.get_json()["name"] == "Netflix"

    data = client.get("/subscriptions").get_json()
    assert data["subscriptions"] == []
    assert data["cancelled"][0]["name"] == "Netflix"
    assert data["yearly_savings_cents"] == 16188


def test_cancel_only_works_with_post(client):
    sub_id = add_netflix(client)
    response = client.get(f"/subscriptions/{sub_id}/cancel")
    assert response.status_code == 405
    assert response.get_json()["error"]


def test_a_cancelled_subscription_cannot_be_edited(client):
    sub_id = add_netflix(client)
    client.post(f"/subscriptions/{sub_id}/cancel")
    assert client.get(f"/subscriptions/{sub_id}").status_code == 404
    assert client.put(f"/subscriptions/{sub_id}", json=NETFLIX).status_code == 404


def test_a_price_rise_is_in_the_list_and_the_history(client):
    sub_id = add_netflix(client)
    client.put(f"/subscriptions/{sub_id}", json=dict(NETFLIX, price="15.99"))

    netflix = client.get("/subscriptions").get_json()["subscriptions"][0]
    assert netflix["price_change_percent"] == 19
    assert netflix["original_price_cents"] == 1349

    history = client.get(f"/subscriptions/{sub_id}").get_json()["history"]
    assert history[0]["old_price_cents"] == 1349
    assert history[0]["new_price_cents"] == 1599


def test_the_seam_endpoint_gives_the_active_subscriptions(client):
    """GET /subscriptions/active is what the Budgets service calls."""
    sub_id = add_netflix(client)
    client.post("/subscriptions", json=dict(NETFLIX, name="Spotify", category="Music"))
    client.post(f"/subscriptions/{sub_id}/cancel")

    subs = client.get("/subscriptions/active").get_json()["subscriptions"]
    assert [sub["name"] for sub in subs] == ["Spotify"]
    assert subs[0]["monthly_cost_cents"] == 1349
    assert "next_payment_date" in subs[0]


def test_unknown_addresses_answer_json(client):
    response = client.get("/nothing-here")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Not found."
