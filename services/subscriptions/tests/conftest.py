import pytest

import db
from accounts import repository as accounts_repository
from app import create_app
from subscriptions import repository as subscriptions_repository

TEST_SECRET_KEY = "only-for-tests-not-a-real-secret"


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point DATA_DIR at a fresh temporary folder so tests never touch real data."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    db.init_db([
        accounts_repository.CREATE_TABLE,
        subscriptions_repository.CREATE_TABLE,
        subscriptions_repository.CREATE_PRICE_CHANGES_TABLE,
    ])


@pytest.fixture
def guest(tmp_path, monkeypatch):
    """A pretend browser with NO token, talking to a fresh app with its own temporary database."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET_KEY)
    return create_app().test_client()


def log_in_as(browser, token):
    """Make the pretend browser send this token with every request, like the real pages do."""
    browser.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"


@pytest.fixture
def client(guest):
    """The same pretend browser after signing up, so it sends a valid token."""
    response = guest.post("/register", json={
        "email": "student@example.com",
        "password": "secret-pass",
        "confirm_password": "secret-pass",
    })
    log_in_as(guest, response.get_json()["token"])
    return guest
