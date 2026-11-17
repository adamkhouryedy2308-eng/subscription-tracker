"""Shared test setup: every test that needs the database gets the EMPTY subscriptions_test database.

Locally, start SQL Server first (docker compose up -d); the password is read from the
.env file at the repository root. In CI, TEST_DATABASE_URL is set instead.
"""
import os
from urllib.parse import quote

import pytest

import db
from app import create_app

TEST_SECRET_KEY = "only-for-tests-not-a-real-secret"
ENV_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
TABLES = ["price_changes", "subscriptions", "users"]  # children before parents (foreign key)


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
    password = read_env_file(ENV_FILE).get("SUBSCRIPTIONS_DB_PASSWORD")
    if not password:
        pytest.exit("No database for the tests: create .env and run `docker compose up -d`, "
                    "or set TEST_DATABASE_URL.")
    return f"mssql://subscriptions_user:{quote(password, safe='')}@localhost:1433/subscriptions_test"


test_database_url.__test__ = False  # its name starts with "test", but it is not a test


@pytest.fixture(scope="session", autouse=True)
def fresh_schema():
    """Once per test run: remove every table and build them again with the migrations."""
    os.environ["DATABASE_URL"] = test_database_url()
    for table in TABLES + ["schema_migrations"]:
        db.execute(f"IF OBJECT_ID('{table}', 'U') IS NOT NULL DROP TABLE {table}")
    db.run_migrations()


@pytest.fixture
def temp_db():
    """Empty every table, so the test starts with no users and no subscriptions."""
    for table in TABLES:
        db.execute(f"DELETE FROM {table}")


@pytest.fixture
def guest(temp_db, monkeypatch):
    """A pretend browser with NO token, talking to a fresh app and an empty database."""
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
