"""Tests for the "phone" to the Subscriptions service, with real HTTP calls to a tiny fake server."""
import json
import threading
import time
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import subscriptions_client

NETFLIX_AS_JSON = {
    "name": "Netflix", "category": "Entertainment", "price_cents": 1349,
    "first_payment_date": "2026-01-15", "next_payment_date": "2026-11-15",
    "last_price_change": {"old_price_cents": 1199, "new_price_cents": 1349,
                          "changed_date": "2026-10-01", "percent": 13},
}


class FakeSubscriptionsService(BaseHTTPRequestHandler):
    """Answers GET /subscriptions/active the way the test asks (see the `behaviour` field)."""
    behaviour = "ok"
    last_authorization = None

    def do_GET(self):
        FakeSubscriptionsService.last_authorization = self.headers.get("Authorization")
        if self.behaviour == "slow":
            time.sleep(1)
        if self.behaviour == "crash":
            self.send_response(500)
            self.end_headers()
            return
        body = b"not json" if self.behaviour == "garbage" else json.dumps(
            {"subscriptions": [dict(NETFLIX_AS_JSON)]}).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        """Keep the test output quiet."""


@pytest.fixture
def fake_server(monkeypatch):
    """Start the fake service on a free port and point SUBSCRIPTIONS_URL at it."""
    server = HTTPServer(("127.0.0.1", 0), FakeSubscriptionsService)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("SUBSCRIPTIONS_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("SUBSCRIPTIONS_TIMEOUT_S", "0.3")
    FakeSubscriptionsService.behaviour = "ok"
    yield FakeSubscriptionsService
    server.shutdown()
    server.server_close()


def test_reads_the_subscriptions_and_turns_dates_back_into_dates(fake_server):
    subs = subscriptions_client.get_active_subscriptions("my-token")
    assert subs[0]["name"] == "Netflix"
    assert subs[0]["next_payment_date"] == date(2026, 11, 15)
    assert subs[0]["last_price_change"]["changed_date"] == date(2026, 10, 1)


def test_passes_on_the_users_token(fake_server):
    subscriptions_client.get_active_subscriptions("my-token")
    assert fake_server.last_authorization == "Bearer my-token"


@pytest.mark.parametrize("behaviour", ["slow", "crash", "garbage"])
def test_a_slow_crashing_or_strange_answer_raises_unavailable(fake_server, behaviour):
    fake_server.behaviour = behaviour
    with pytest.raises(subscriptions_client.SubscriptionsUnavailable):
        subscriptions_client.get_active_subscriptions("my-token")


def test_a_service_that_is_not_running_raises_unavailable(monkeypatch):
    monkeypatch.setenv("SUBSCRIPTIONS_URL", "http://127.0.0.1:1")  # nothing listens on port 1
    with pytest.raises(subscriptions_client.SubscriptionsUnavailable):
        subscriptions_client.get_active_subscriptions("my-token")


def test_only_web_addresses_are_called(monkeypatch):
    """A SUBSCRIPTIONS_URL like file:///etc/passwd must never be opened (Bandit B310)."""
    monkeypatch.setenv("SUBSCRIPTIONS_URL", "file:///etc/passwd")
    with pytest.raises(subscriptions_client.SubscriptionsUnavailable):
        subscriptions_client.get_active_subscriptions("token")


def test_a_subscription_without_a_price_change_keeps_none():
    sub = subscriptions_client.with_dates(dict(NETFLIX_AS_JSON, last_price_change=None))
    assert sub["last_price_change"] is None


def test_defaults_point_at_the_compose_service_with_a_2_second_timeout(monkeypatch):
    monkeypatch.delenv("SUBSCRIPTIONS_URL", raising=False)
    monkeypatch.delenv("SUBSCRIPTIONS_TIMEOUT_S", raising=False)
    assert subscriptions_client.base_url() == "http://subscriptions:8000"
    assert subscriptions_client.timeout_seconds() == 2
