"""Integration test ACROSS the seam: both real services running, talking over real HTTP.

Unlike each service's own tests (where the other service is a stand-in), this
test starts the real Subscriptions and Budgets & Alerts services as two separate
programs on this machine, uses them like the browser does, and then stops
Subscriptions to check that Budgets fails in the designed way.

Run it from the repository root, with SQL Server running (docker compose up -d):  pytest
"""
import json
import os
import socket
import subprocess
import sys
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = "only-for-tests-not-a-real-secret"   # both services get the SAME key


def read_env_file():
    """Read NAME=value lines from the .env file at the repository root."""
    values = {}
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        with open(path) as file:
            for line in file:
                name, equals, value = line.strip().partition("=")
                if equals and not name.startswith("#"):
                    values[name] = value
    return values


def database_url(service):
    """Each service's own TEST database, with its own login (from CI's variables or from .env)."""
    variable = f"{service.upper()}_TEST_DATABASE_URL"
    if os.environ.get(variable):
        return os.environ[variable]
    password = read_env_file().get(f"{service.upper()}_DB_PASSWORD")
    if not password:
        pytest.exit("No database: create .env and run `docker compose up -d`, or set " + variable)
    return f"mssql://{service}_user:{quote(password, safe='')}@localhost:1433/{service}_test"


def free_port():
    """Ask the computer for a port nobody is using."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_service(name, port, extra_env=None):
    """Start one service with `python app.py`, configured only through environment variables."""
    env = dict(os.environ, SECRET_KEY=SECRET_KEY, PORT=str(port), DATABASE_URL=database_url(name))
    env.update(extra_env or {})
    process = subprocess.Popen([sys.executable, "app.py"], cwd=os.path.join(ROOT, "services", name),
                               env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_until_answering(f"http://127.0.0.1:{port}")
    return process


def wait_until_answering(base_url, seconds=60):
    """Wait until the service answers anything at all (401 is fine: it means it is up)."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            urlopen(base_url + "/nothing", timeout=1)
        except HTTPError:
            return
        except URLError:
            time.sleep(0.2)
    raise RuntimeError(f"{base_url} did not start")


def call(method, url, body=None, token=None):
    """Send one request like the browser does. Returns (status code, JSON answer)."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


@pytest.fixture
def system():
    """Both services, each with its own database and login, Budgets pointing at Subscriptions."""
    subs_port, budgets_port = free_port(), free_port()
    subscriptions = start_service("subscriptions", subs_port)
    budgets = start_service("budgets", budgets_port, {
        "SUBSCRIPTIONS_URL": f"http://127.0.0.1:{subs_port}",
        "SUBSCRIPTIONS_TIMEOUT_S": "2",
    })
    yield {"subscriptions": f"http://127.0.0.1:{subs_port}", "budgets": f"http://127.0.0.1:{budgets_port}",
           "subscriptions_process": subscriptions}
    for process in (subscriptions, budgets):
        process.terminate()
        process.wait()


def test_budgets_reads_subscriptions_across_the_seam_and_survives_when_it_is_down(system):
    subs, budgets = system["subscriptions"], system["budgets"]

    # 1. Sign up on Subscriptions (a new email every run): it gives back a token.
    email = f"seam-{uuid.uuid4().hex[:8]}@example.com"
    status, answer = call("POST", subs + "/register", {
        "email": email, "password": "secret-pass", "confirm_password": "secret-pass"})
    assert status == 201
    token = answer["token"]

    # 2. Add Netflix on Subscriptions, and a 10 euro Entertainment budget on Budgets.
    status, _ = call("POST", subs + "/subscriptions", {
        "name": "Netflix", "category": "Entertainment", "price": "13.49",
        "billing_cycle": "monthly", "first_payment_date": "2026-01-15"}, token)
    assert status == 201
    status, _ = call("POST", budgets + "/budgets", {"category": "Entertainment", "amount": "10"}, token)
    assert status == 200

    # 3. THE SEAM: Budgets calls Subscriptions over HTTP, with the same token, and finds Netflix.
    status, answer = call("GET", budgets + "/budgets", token=token)
    assert status == 200
    assert answer["spending_available"] is True
    row = answer["rows"][0]
    assert (row["category"], row["monthly_cents"], row["status"]) == ("Entertainment", 1349, "over")

    status, answer = call("GET", budgets + "/alerts", token=token)
    assert status == 200
    assert [alert["kind"] for alert in answer["alerts"]] == ["over_budget"]

    # 4. PARTIAL FAILURE: stop Subscriptions, like `docker compose stop subscriptions`.
    system["subscriptions_process"].terminate()
    system["subscriptions_process"].wait()

    started = time.time()
    status, answer = call("GET", budgets + "/budgets", token=token)
    assert time.time() - started < 5            # it gives up quickly instead of hanging
    assert status == 200                        # Budgets still serves its own domain...
    assert answer["spending_available"] is False
    assert answer["budgets"] == {"Entertainment": 1000}   # ...with the budgets from its own database
    assert "Subscriptions service is not answering" in answer["message"]

    status, answer = call("GET", budgets + "/alerts", token=token)
    assert status == 503
    assert "Subscriptions service is not answering" in answer["error"]

    # Saving a budget does not need Subscriptions at all.
    status, _ = call("POST", budgets + "/budgets", {"category": "Music", "amount": "15"}, token)
    assert status == 200
