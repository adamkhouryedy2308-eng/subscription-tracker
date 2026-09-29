import pytest

import db
from subscriptions import repository as subscriptions_repository


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point DATA_DIR at a fresh temporary folder so tests never touch real data."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    db.init_db([subscriptions_repository.CREATE_TABLE])
