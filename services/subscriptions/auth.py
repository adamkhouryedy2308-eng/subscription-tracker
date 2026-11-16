"""Login tickets (tokens): made when you log in, checked on every request.

A token is the user's id plus a stamp (signature) made with SECRET_KEY.
Anyone can read the id inside, but without the key nobody can make a stamp
that matches, so a changed or invented token is refused. The Budgets service
has the same key, so it can check tokens without calling this service.
"""
from flask import current_app, request
from itsdangerous import BadSignature, URLSafeTimedSerializer

TOKEN_DAYS = 7


def stamper():
    """The tool that stamps and checks tokens with the secret key."""
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="subtrack-login")


def make_token(user_id):
    """A new token for this user, e.g. after logging in."""
    return stamper().dumps({"user_id": user_id})


def read_token(token):
    """The user id inside a token, or None if the stamp is wrong or the token is too old."""
    try:
        data = stamper().loads(token, max_age=TOKEN_DAYS * 24 * 60 * 60)
    except BadSignature:  # also covers a token older than TOKEN_DAYS
        return None
    return data["user_id"]


def user_id_from_request():
    """Read the "Authorization: Bearer <token>" header the browser sends with every request."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return read_token(header[len("Bearer "):])
