"""Tests for the migration runner and the database connection in db.py."""
import os

import pymssql
import pytest

import db


def applied_versions():
    return [row["version"] for row in db.query("SELECT version FROM schema_migrations ORDER BY version")]


def test_the_real_migrations_are_recorded_once():
    assert applied_versions() == ["001_init.sql", "002_health_check.sql", "003_budget_warn_percent.sql"]


def test_a_second_start_applies_nothing():
    assert db.run_migrations() == []


def test_a_new_migration_runs_once_and_keeps_existing_rows(tmp_path, temp_db):
    """Like a real 00X file: it changes a table that already holds data, without losing it."""
    db.execute("CREATE TABLE migration_test (id INT PRIMARY KEY, name NVARCHAR(50))")
    db.execute("INSERT INTO migration_test VALUES (1, 'kept')")
    (tmp_path / "901_add_column.sql").write_text(
        "ALTER TABLE migration_test ADD note NVARCHAR(50) NULL;\nGO\n"
        "UPDATE migration_test SET note = 'filled in';\n")
    try:
        assert db.run_migrations(str(tmp_path)) == ["901_add_column.sql"]
        assert db.run_migrations(str(tmp_path)) == []          # exactly once
        assert db.query("SELECT * FROM migration_test") == [{"id": 1, "name": "kept", "note": "filled in"}]
    finally:
        db.execute("DROP TABLE migration_test")
        db.execute("DELETE FROM schema_migrations WHERE version = '901_add_column.sql'")


def test_migration_003_keeps_the_budgets_that_already_exist(tmp_path):
    """What happens on Azure: budgets saved BEFORE 003 are still there after it, warning at 80%."""
    # Go back to the database as it was before 003: only 001's budgets table, with data in it.
    db.execute("DROP TABLE budgets")
    db.execute("DELETE FROM schema_migrations WHERE version IN ('001_init.sql', '003_budget_warn_percent.sql')")
    (tmp_path / "001_init.sql").write_text(open(os.path.join(db.MIGRATIONS_DIR, "001_init.sql")).read())
    assert db.run_migrations(str(tmp_path)) == ["001_init.sql"]
    db.execute("INSERT INTO budgets (user_id, category, monthly_limit_cents) VALUES (7, 'Music', 1500)")
    db.execute("INSERT INTO budgets (user_id, category, monthly_limit_cents) VALUES (7, 'Education', 4000)")

    # Start the service again: only 003 runs, and both rows are kept with the default 80%.
    assert db.run_migrations() == ["003_budget_warn_percent.sql"]
    rows = db.query("SELECT user_id, category, monthly_limit_cents, warn_percent FROM budgets ORDER BY id")
    assert rows == [
        {"user_id": 7, "category": "Music", "monthly_limit_cents": 1500, "warn_percent": 80},
        {"user_id": 7, "category": "Education", "monthly_limit_cents": 4000, "warn_percent": 80},
    ]
    db.execute("DELETE FROM budgets")


def test_the_database_refuses_a_warning_level_outside_1_to_100(temp_db):
    with pytest.raises(pymssql.Error):
        db.execute("INSERT INTO budgets (user_id, category, monthly_limit_cents, warn_percent) "
                   "VALUES (1, 'Music', 1500, 150)")


def test_a_failing_migration_leaves_no_trace(tmp_path):
    (tmp_path / "902_broken.sql").write_text("CREATE TABLE half_done (id INT);\nGO\nTHIS IS NOT SQL;\n")
    with pytest.raises(pymssql.Error):
        db.run_migrations(str(tmp_path))
    assert "902_broken.sql" not in applied_versions()
    assert db.query_one("SELECT OBJECT_ID('half_done', 'U') AS id")["id"] is None


def test_files_that_are_not_sql_are_ignored(tmp_path):
    (tmp_path / "README.md").write_text("notes")
    assert db.run_migrations(str(tmp_path)) == []


def test_split_batches_cuts_on_go_lines():
    assert db.split_batches("A;\nGO\nB;\n  go  \n\nC;") == ["A;", "B;", "\nC;"]


def test_connect_with_retry_tries_again_then_succeeds(monkeypatch):
    calls = []

    def flaky_connect():
        calls.append(1)
        if len(calls) < 3:
            raise pymssql.OperationalError("database is resuming")
        return "connection"

    monkeypatch.setattr(db, "connect", flaky_connect)
    monkeypatch.setattr(db.time, "sleep", lambda seconds: None)   # do not really wait
    assert db.connect_with_retry() == "connection"
    assert len(calls) == 3


def test_connect_with_retry_gives_up_after_the_last_attempt(monkeypatch):
    def always_fails():
        raise pymssql.OperationalError("no database")

    monkeypatch.setattr(db, "connect", always_fails)
    monkeypatch.setattr(db.time, "sleep", lambda seconds: None)
    with pytest.raises(pymssql.OperationalError):
        db.connect_with_retry(attempts=3)
