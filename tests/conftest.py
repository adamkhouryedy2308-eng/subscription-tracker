import pytest

import db
from app import create_app
from subscriptions import repository as subscriptions_repository


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point DATA_DIR at a fresh temporary folder so tests never touch real data."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    db.init_db([subscriptions_repository.CREATE_TABLE])


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A pretend browser that talks to a fresh app with its own temporary database."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return create_app().test_client()
