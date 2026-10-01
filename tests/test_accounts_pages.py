import os

import app as app_module
from tests.test_subscriptions_pages import NETFLIX

ANA = {"email": "ana@example.com", "password": "secret-pass", "confirm_password": "secret-pass"}
BEN = {"email": "ben@example.com", "password": "other-pass", "confirm_password": "other-pass"}


# --- Pages that need a login -----------------------------------------------------

def test_visitors_are_sent_to_the_login_page(guest):
    for url in ["/", "/subscriptions/", "/subscriptions/new", "/subscriptions/1/edit"]:
        response = guest.get(url)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")


def test_login_and_register_pages_and_the_stylesheet_are_open_to_everyone(guest):
    assert "Welcome back" in guest.get("/login").get_data(as_text=True)
    assert "Create your account" in guest.get("/register").get_data(as_text=True)
    assert guest.get("/static/style.css").status_code == 200


def test_a_session_for_a_deleted_user_is_sent_to_log_in(guest):
    with guest.session_transaction() as session:
        session["user_id"] = 99
    assert guest.get("/subscriptions/").headers["Location"].endswith("/login")


# --- Signing up, logging in and out ---------------------------------------------

def test_signing_up_logs_you_in(guest):
    response = guest.post("/register", data=ANA)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/subscriptions/")
    assert "ana@example.com" in guest.get("/subscriptions/").get_data(as_text=True)


def test_signing_up_with_mistakes_shows_the_errors(guest):
    form = dict(ANA)
    form["confirm_password"] = "different"
    response = guest.post("/register", data=form)
    page = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "The two passwords do not match." in page
    assert 'value="ana@example.com"' in page


def test_logging_in_with_the_right_password(guest):
    guest.post("/register", data=ANA)
    guest.post("/logout")
    response = guest.post("/login", data={"email": "ana@example.com", "password": "secret-pass"})
    assert response.status_code == 302
    assert guest.get("/subscriptions/").status_code == 200


def test_logging_in_with_a_wrong_password_shows_one_general_message(guest):
    guest.post("/register", data=ANA)
    guest.post("/logout")
    response = guest.post("/login", data={"email": "ana@example.com", "password": "wrong-pass"})
    assert response.status_code == 400
    assert "Wrong email or password." in response.get_data(as_text=True)
    assert guest.get("/subscriptions/").status_code == 302


def test_logging_out_ends_the_session(client):
    response = client.post("/logout")
    assert response.headers["Location"].endswith("/login")
    assert client.get("/subscriptions/").status_code == 302


def test_logout_only_works_with_post(client):
    assert client.get("/logout").status_code == 405


# --- Privacy between users -----------------------------------------------------

def test_users_never_see_or_change_each_others_subscriptions(guest):
    guest.post("/register", data=ANA)
    guest.post("/subscriptions/new", data=NETFLIX)
    guest.post("/logout")

    guest.post("/register", data=BEN)
    page = guest.get("/subscriptions/").get_data(as_text=True)
    assert "No subscriptions yet" in page
    assert "€13.49" not in page
    assert guest.get("/subscriptions/1/edit").status_code == 404
    assert guest.post("/subscriptions/1/cancel").status_code == 404

    guest.post("/logout")
    guest.post("/login", data={"email": "ana@example.com", "password": "secret-pass"})
    assert "€13.49" in guest.get("/subscriptions/").get_data(as_text=True)


# --- The secret key that signs the login cookie ---------------------------------

def test_secret_key_is_made_once_and_kept_in_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    first = app_module.get_secret_key()
    second = app_module.get_secret_key()
    assert first == second
    assert len(first) == 64
    assert os.path.exists(tmp_path / "secret_key.txt")
