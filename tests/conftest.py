import pytest

import db
from accounts import repository as accounts_repository
from app import create_app
from budgets import repository as budgets_repository
from subscriptions import repository as subscriptions_repository


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point DATA_DIR at a fresh temporary folder so tests never touch real data."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    db.init_db([
        accounts_repository.CREATE_TABLE,
        subscriptions_repository.CREATE_TABLE,
        budgets_repository.CREATE_TABLE,
    ])


@pytest.fixture
def guest(tmp_path, monkeypatch):
    """A pretend browser that is NOT logged in, talking to a fresh app with its own temporary database."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return create_app().test_client()


@pytest.fixture
def client(guest):
    """The same pretend browser after signing up, so it is logged in."""
    guest.post("/register", data={
        "email": "student@example.com",
        "password": "secret-pass",
        "confirm_password": "secret-pass",
    })
    return guest
