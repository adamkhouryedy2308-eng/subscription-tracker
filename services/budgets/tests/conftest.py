import pytest
from itsdangerous import URLSafeTimedSerializer

import db
import subscriptions_client
from app import create_app
from budgets import repository as budgets_repository

TEST_SECRET_KEY = "only-for-tests-not-a-real-secret"


def make_token(user_id, key=TEST_SECRET_KEY):
    """A token like the Subscriptions service gives at login (Budgets itself never makes one)."""
    return URLSafeTimedSerializer(key, salt="subtrack-login").dumps({"user_id": user_id})


def log_in_as(browser, user_id):
    """Make the pretend browser send a token for this user with every request."""
    browser.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {make_token(user_id)}"


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point DATA_DIR at a fresh temporary folder so tests never touch real data."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    db.init_db([budgets_repository.CREATE_TABLE])


@pytest.fixture
def guest(tmp_path, monkeypatch):
    """A pretend browser with NO token, talking to a fresh app with its own temporary database."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET_KEY)
    return create_app().test_client()


@pytest.fixture
def client(guest):
    """The same pretend browser logged in as user 1."""
    log_in_as(guest, 1)
    return guest


@pytest.fixture
def fake_subscriptions(monkeypatch):
    """A stand-in for the Subscriptions service (a "stub"), so these tests need only this service.

    Tests put subscriptions in the returned dict under the user's token; the
    real call over HTTP is tested separately in test_subscriptions_client.py.
    """
    answers = {"subscriptions": [], "down": False}

    def fake_get_active_subscriptions(token):
        if answers["down"]:
            raise subscriptions_client.SubscriptionsUnavailable()
        return answers["subscriptions"]

    monkeypatch.setattr(subscriptions_client, "get_active_subscriptions", fake_get_active_subscriptions)
    return answers
