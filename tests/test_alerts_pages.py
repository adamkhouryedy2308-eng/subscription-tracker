from datetime import date, timedelta

from tests.test_subscriptions_pages import NETFLIX

BEN = {"email": "ben@example.com", "password": "other-pass", "confirm_password": "other-pass"}


def in_days(days):
    return (date.today() + timedelta(days=days)).isoformat()


def test_visitors_are_sent_to_log_in(guest):
    assert guest.get("/budgets/alerts").headers["Location"].endswith("/login")


def test_no_alerts_means_all_clear_and_no_badge(client):
    page = client.get("/budgets/alerts").get_data(as_text=True)
    assert "All clear" in page
    assert "nav-badge" not in page


def test_payment_soon_is_shown_with_a_badge_on_every_page(client):
    form = dict(NETFLIX, first_payment_date=in_days(2))
    client.post("/subscriptions/new", data=form)
    page = client.get("/budgets/alerts").get_data(as_text=True)
    assert "Payment soon" in page
    assert "charges €13.49 in 2 days" in page
    assert 'class="nav-badge"' in client.get("/subscriptions/").get_data(as_text=True)


def test_every_kind_of_alert_is_shown(client):
    client.post("/subscriptions/new", data=dict(NETFLIX, first_payment_date=in_days(1),
                                                last_used_date=in_days(-40)))
    client.post("/subscriptions/new", data=dict(NETFLIX, name="Disney+", price="8.99",
                                                first_payment_date=in_days(0), is_trial="on"))
    client.post("/budgets/", data={"category": "Entertainment", "amount": "15"})

    page = client.get("/budgets/alerts").get_data(as_text=True)
    assert "turns into a paid plan today" in page
    assert "€7.48 more than your €15.00 budget" in page
    assert "charges €13.49 tomorrow" in page
    assert "for 40 days but still pay €13.49 a month" in page
    assert page.index("Free trial ending") < page.index("Over budget") < page.index("Payment soon")


def test_other_users_never_see_my_alerts(client):
    client.post("/subscriptions/new", data=dict(NETFLIX, first_payment_date=in_days(2)))
    client.post("/logout")
    client.post("/register", data=BEN)
    assert "All clear" in client.get("/budgets/alerts").get_data(as_text=True)



def test_a_price_rise_shows_an_alert(client):
    client.post("/subscriptions/new", data=dict(NETFLIX, first_payment_date=in_days(20)))
    client.post("/subscriptions/1/edit", data=dict(NETFLIX, first_payment_date=in_days(20), price="15.99"))
    page = client.get("/budgets/alerts").get_data(as_text=True)
    assert "Price went up" in page
    assert "went up from €13.49 to €15.99 (+19%)" in page
