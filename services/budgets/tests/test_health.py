"""GET /health and the one log line per request."""
import pymssql

import db


def test_health_is_ok_without_logging_in(guest, monkeypatch):
    monkeypatch.setenv("GIT_SHA", "abc1234")
    response = guest.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "db": "ok", "version": "abc1234"}


def test_health_says_dev_when_no_version_is_set(guest, monkeypatch):
    monkeypatch.delenv("GIT_SHA", raising=False)
    assert guest.get("/health").get_json()["version"] == "dev"


def test_health_is_503_when_the_database_is_down(guest, monkeypatch):
    def broken_connect():
        raise pymssql.OperationalError("database is down")

    monkeypatch.setattr(db, "connect", broken_connect)
    response = guest.get("/health")
    assert response.status_code == 503
    assert response.get_json()["db"] == "unavailable"


def test_health_really_writes_to_the_database(guest):
    before = db.query_one("SELECT checked_at FROM health_check")["checked_at"]
    guest.get("/health")
    after = db.query_one("SELECT checked_at FROM health_check")["checked_at"]
    assert after > before


def test_every_request_is_logged_with_method_path_status_and_duration(guest, capsys):
    guest.get("/health")
    guest.get("/no-such-page")
    lines = capsys.readouterr().out.splitlines()
    assert lines[-2].startswith("GET /health 200 ")
    assert lines[-2].endswith("ms")
    assert lines[-1].startswith("GET /no-such-page 401 ")   # unknown pages need a login first


def test_the_log_never_contains_the_token(guest, capsys):
    guest.get("/health", headers={"Authorization": "Bearer secret-token-value"})
    assert "secret-token-value" not in capsys.readouterr().out


def test_every_answer_has_the_security_headers(guest):
    """Found missing by the DAST scan (OWASP ZAP): even errors carry them."""
    for url in ["/health", "/nothing-here"]:
        headers = guest.get(url).headers
        assert headers["Strict-Transport-Security"] == "max-age=31536000"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
        assert headers["Cache-Control"] == "no-store"
