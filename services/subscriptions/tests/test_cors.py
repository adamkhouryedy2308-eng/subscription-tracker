"""CORS: only the UI's address may call this service from a browser."""
import pytest

import app

UI = "http://localhost:8080"


@pytest.fixture
def browser(temp_db, monkeypatch):
    """A fresh app that allows only the UI's address."""
    monkeypatch.setenv("SECRET_KEY", "only-for-tests-not-a-real-secret")
    monkeypatch.setenv("CORS_ORIGINS", UI)
    return app.create_app().test_client()


def ask_first(browser, origin):
    """The browser's question before a JSON POST from another address (a "preflight")."""
    return browser.options("/subscriptions", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type, Authorization",
    })


def test_the_ui_may_send_json_with_a_token(browser):
    response = ask_first(browser, UI)
    assert response.status_code == 200                      # no login needed to ask
    assert response.headers["Access-Control-Allow-Origin"] == UI
    allowed = response.headers["Access-Control-Allow-Headers"].lower()
    assert "content-type" in allowed and "authorization" in allowed


def test_another_website_is_not_allowed(browser):
    response = ask_first(browser, "https://evil.example.com")
    assert "Access-Control-Allow-Origin" not in response.headers


def test_normal_answers_tell_the_browser_the_ui_may_read_them(browser):
    response = browser.get("/health", headers={"Origin": UI})
    assert response.headers["Access-Control-Allow-Origin"] == UI


def test_without_cors_origins_no_website_is_allowed(temp_db, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "only-for-tests-not-a-real-secret")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    response = ask_first(app.create_app().test_client(), UI)
    assert "Access-Control-Allow-Origin" not in response.headers


def test_cors_origins_can_hold_several_addresses(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", " http://localhost:8080 , https://ui.example.com ,")
    assert app.cors_origins() == ["http://localhost:8080", "https://ui.example.com"]
