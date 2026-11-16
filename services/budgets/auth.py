"""Checking login tokens. Budgets never makes tokens; the Subscriptions service does at login.

Both services have the same SECRET_KEY, so Budgets can check a token's stamp
itself, without calling Subscriptions. This keeps Budgets working when
Subscriptions is down.
"""
from flask import current_app, request
from itsdangerous import BadSignature, URLSafeTimedSerializer

TOKEN_DAYS = 7  # must match the Subscriptions service


def read_token(token):
    """The user id inside a token, or None if the stamp is wrong or the token is too old."""
    stamper = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="subtrack-login")
    try:
        data = stamper.loads(token, max_age=TOKEN_DAYS * 24 * 60 * 60)
    except BadSignature:  # also covers a token older than TOKEN_DAYS
        return None
    return data["user_id"]


def token_from_request():
    """The token in the "Authorization: Bearer <token>" header, or None."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return header[len("Bearer "):]
