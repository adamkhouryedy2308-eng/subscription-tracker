import pytest
from itsdangerous import URLSafeTimedSerializer

import app as app_module
import auth
from tests.conftest import log_in_as
from tests.test_subscriptions_pages import NETFLIX

ANA = {"email": "ana@example.com", "password": "secret-pass", "confirm_password": "secret-pass"}
BEN = {"email": "ben@example.com", "password": "other-pass", "confirm_password": "other-pass"}


def sign_up(browser, form):
    """Sign up and start sending the new token. Returns the token."""
    token = browser.post("/register", json=form).get_json()["token"]
    log_in_as(browser, token)
    return token


# --- Endpoints that need a login ------------------------------------------------

def test_requests_without_a_token_get_401(guest):
    for url in ["/subscriptions", "/subscriptions/active", "/subscriptions/1", "/me"]:
        response = guest.get(url)
        assert response.status_code == 401
        assert response.get_json()["error"] == "Log in first."


def test_a_fake_or_changed_token_is_refused(guest):
    token = sign_up(guest, ANA)
    log_in_as(guest, token + "x")
    assert guest.get("/me").status_code == 401
    log_in_as(guest, "made-up-token")
    assert guest.get("/me").status_code == 401


def test_a_token_stamped_with_another_key_is_refused(guest):
    sign_up(guest, ANA)
    forged = URLSafeTimedSerializer("some-other-key", salt="subtrack-login").dumps({"user_id": 1})
    log_in_as(guest, forged)
    assert guest.get("/me").status_code == 401


def test_a_token_for_a_deleted_user_is_refused(guest):
    with guest.application.app_context():
        token = auth.make_token(99)
    log_in_as(guest, token)
    assert guest.get("/subscriptions").status_code == 401


def test_the_header_must_start_with_bearer(guest):
    guest.environ_base["HTTP_AUTHORIZATION"] = "Basic something"
    assert guest.get("/me").status_code == 401


# --- Signing up and logging in ----------------------------------------------------

def test_signing_up_gives_a_token(guest):
    response = guest.post("/register", json=ANA)
    assert response.status_code == 201
    log_in_as(guest, response.get_json()["token"])
    assert guest.get("/me").get_json()["email"] == "ana@example.com"


def test_signing_up_with_mistakes_gives_the_errors(guest):
    response = guest.post("/register", json=dict(ANA, confirm_password="different"))
    assert response.status_code == 400
    assert "The two passwords do not match." in response.get_json()["errors"]


def test_signing_up_without_a_body_gives_errors(guest):
    assert guest.post("/register").status_code == 400


def test_logging_in_with_the_right_password(guest):
    guest.post("/register", json=ANA)
    response = guest.post("/login", json={"email": "ana@example.com", "password": "secret-pass"})
    assert response.status_code == 200
    log_in_as(guest, response.get_json()["token"])
    assert guest.get("/subscriptions").status_code == 200


def test_logging_in_with_a_wrong_password_gives_one_general_message(guest):
    guest.post("/register", json=ANA)
    response = guest.post("/login", json={"email": "ana@example.com", "password": "wrong-pass"})
    assert response.status_code == 401
    assert response.get_json() == {"error": "Wrong email or password."}


# --- Privacy between users ----------------------------------------------------------

def test_users_never_see_or_change_each_others_subscriptions(guest):
    ana_token = sign_up(guest, ANA)
    anas_id = guest.post("/subscriptions", json=NETFLIX).get_json()["id"]

    sign_up(guest, BEN)
    assert guest.get("/subscriptions").get_json()["subscriptions"] == []
    assert guest.get("/subscriptions/active").get_json()["subscriptions"] == []
    assert guest.get(f"/subscriptions/{anas_id}").status_code == 404
    assert guest.put(f"/subscriptions/{anas_id}", json=NETFLIX).status_code == 404
    assert guest.post(f"/subscriptions/{anas_id}/cancel").status_code == 404

    log_in_as(guest, ana_token)
    assert guest.get("/subscriptions").get_json()["subscriptions"][0]["name"] == "Netflix"


# --- The secret key that stamps the tokens ----------------------------------------

def test_the_secret_key_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "abc")
    assert app_module.get_secret_key() == "abc"


def test_the_service_refuses_to_start_without_a_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        app_module.get_secret_key()
