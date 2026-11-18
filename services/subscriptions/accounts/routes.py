"""Account endpoints: sign up and log in. Every answer is JSON."""
from datetime import date

from flask import Blueprint, g, jsonify, request

import auth
from accounts import service

bp = Blueprint("accounts", __name__)

# Endpoints a visitor may use without logging in. Every other one needs a token.
PUBLIC_ENDPOINTS = ["accounts.register", "accounts.login", "health"]


@bp.before_app_request
def require_login():
    """Runs before every request: find who is logged in, or answer 401 (not logged in)."""
    g.user = None
    user_id = auth.user_id_from_request()
    if user_id is not None:
        g.user = service.get_user(user_id)
    if g.user is None and request.endpoint not in PUBLIC_ENDPOINTS:
        return jsonify(error="Log in first."), 401


@bp.route("/register", methods=["POST"])
def register():
    """Create an account and log the user in straight away (201 = created)."""
    form = request.get_json(silent=True) or {}
    user_id, errors = service.register(form, date.today())
    if errors:
        return jsonify(errors=errors), 400
    return jsonify(token=auth.make_token(user_id)), 201


@bp.route("/login", methods=["POST"])
def login():
    """Check the email and password; give back a token if they match."""
    form = request.get_json(silent=True) or {}
    user_id = service.check_login(form)
    if user_id is None:
        return jsonify(error="Wrong email or password."), 401
    return jsonify(token=auth.make_token(user_id))


@bp.route("/me")
def me():
    """Who is logged in, so the pages can show the email in the sidebar."""
    return jsonify(id=g.user["id"], email=g.user["email"])
