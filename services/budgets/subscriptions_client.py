"""The "phone" to the Subscriptions service: the only way Budgets reads subscription data.

Budgets never opens the Subscriptions database. It asks GET /subscriptions/active
over HTTP, passing on the user's token, and gives up after a few seconds.
"""
import json
import os
from datetime import date
from urllib.error import URLError
from urllib.request import Request, urlopen


class SubscriptionsUnavailable(Exception):
    """The Subscriptions service did not answer in time, or answered with an error."""


def base_url():
    """Where the Subscriptions service is, e.g. http://subscriptions:8000 inside docker compose."""
    return os.environ.get("SUBSCRIPTIONS_URL", "http://subscriptions:8000")


def timeout_seconds():
    """How long to wait for an answer before giving up."""
    return float(os.environ.get("SUBSCRIPTIONS_TIMEOUT_S", "2"))


def get_active_subscriptions(token):
    """This user's active subscriptions, as get_active_subscriptions() in Subscriptions returns them.

    Raises SubscriptionsUnavailable if the call fails or takes longer than the timeout.
    """
    request = Request(base_url() + "/subscriptions/active",
                      headers={"Authorization": f"Bearer {token}"})
    try:
        with urlopen(request, timeout=timeout_seconds()) as response:
            data = json.load(response)
    except (URLError, TimeoutError, ValueError) as error:
        # URLError: no answer or an error status (e.g. 500); TimeoutError: too slow;
        # ValueError: the answer was not JSON.
        raise SubscriptionsUnavailable() from error
    return [with_dates(sub) for sub in data["subscriptions"]]


def with_dates(sub):
    """JSON sends dates as text ("2026-01-15"); turn them back into dates for the alert rules."""
    sub["first_payment_date"] = date.fromisoformat(sub["first_payment_date"])
    sub["next_payment_date"] = date.fromisoformat(sub["next_payment_date"])
    if sub["last_price_change"] is not None:
        change = sub["last_price_change"]
        change["changed_date"] = date.fromisoformat(change["changed_date"])
    return sub
