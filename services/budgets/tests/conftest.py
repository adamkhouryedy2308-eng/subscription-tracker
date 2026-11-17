"""Shared test setup: every test that needs the database gets the EMPTY budgets_test database.

Locally, start SQL Server first (docker compose up -d); the password is read from the
.env file at the repository root. In CI, TEST_DATABASE_URL is set instead.
"""
import os
from urllib.parse import quote

import pytest
from itsdangerous import URLSafeTimedSerializer

import db
import subscriptions_client
from app import create_app

TEST_SECRET_KEY = "only-for-tests-not-a-real-secret"
ENV_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")


def read_env_file(path):
    """Read NAME=value lines from a .env file (empty if the file does not exist)."""
    values = {}
    if os.path.exists(path):
        with open(path) as file:
            for line in file:
                name, equals, value = line.strip().partition("=")
                if equals and not name.startswith("#"):
                    values[name] = value
    return values


def test_database_url():
    """The test database: TEST_DATABASE_URL if set (CI), otherwise built from the password in .env."""
    if os.environ.get("TEST_DATABASE_URL"):
        return os.environ["TEST_DATABASE_URL"]
    password = read_env_file(ENV_FILE).get("BUDGETS_DB_PASSWORD")
    if not password:
        pytest.exit("No database for the tests: create .env and run `docker compose up -d`, "
                    "or set TEST_DATABASE_URL.")
    return f"mssql://budgets_user:{quote(password, safe='')}@localhost:1433/budgets_test"


test_database_url.__test__ = False  # its name starts with "test", but it is not a test


def make_token(user_id, key=TEST_SECRET_KEY):
    """A token like the Subscriptions service gives at login (Budgets itself never makes one)."""
    return URLSafeTimedSerializer(key, salt="subtrack-login").dumps({"user_id": user_id})


def log_in_as(browser, user_id):
    """Make the pretend browser send a token for this user with every request."""
    browser.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {make_token(user_id)}"


@pytest.fixture(scope="session", autouse=True)
def fresh_schema():
    """Once per test run: remove every table and build them again with the migrations."""
    os.environ["DATABASE_URL"] = test_database_url()
    for table in ["budgets", "schema_migrations"]:
        db.execute(f"IF OBJECT_ID('{table}', 'U') IS NOT NULL DROP TABLE {table}")
    db.run_migrations()


@pytest.fixture
def temp_db():
    """Empty the budgets table, so the test starts with no budgets."""
    db.execute("DELETE FROM budgets")


@pytest.fixture
def guest(temp_db, monkeypatch):
    """A pretend browser with NO token, talking to a fresh app and an empty database."""
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
