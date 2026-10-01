"""Web pages for accounts: sign up, log in and log out."""
from datetime import date

from flask import Blueprint, g, redirect, render_template, request, session, url_for

from accounts import service

bp = Blueprint("accounts", __name__)

# Pages a visitor may open without logging in. Every other page needs a login.
PUBLIC_PAGES = ["accounts.login_page", "accounts.register_page", "static"]


@bp.before_app_request
def require_login():
    """Runs before every page of the app: find who is logged in, or send them to log in."""
    g.user = None
    if "user_id" in session:
        g.user = service.get_user(session["user_id"])
    if g.user is None and request.endpoint not in PUBLIC_PAGES:
        return redirect(url_for("accounts.login_page"))


@bp.route("/register", methods=["GET", "POST"])
def register_page():
    """GET shows the sign-up form; POST creates the account and logs the user in."""
    if request.method == "POST":
        user_id, errors = service.register(request.form, date.today())
        if not errors:
            log_in(user_id)
            return redirect(url_for("subscriptions.list_page"))
        return render_template("accounts/register.html", form=request.form, errors=errors), 400
    return render_template("accounts/register.html", form={}, errors=[])


@bp.route("/login", methods=["GET", "POST"])
def login_page():
    """GET shows the login form; POST checks the email and password."""
    if request.method == "POST":
        user_id = service.check_login(request.form)
        if user_id is not None:
            log_in(user_id)
            return redirect(url_for("subscriptions.list_page"))
        return render_template("accounts/login.html", form=request.form,
                               error="Wrong email or password."), 400
    return render_template("accounts/login.html", form={}, error=None)


@bp.route("/logout", methods=["POST"])
def logout():
    """Forget who is logged in. Only POST is allowed, because it changes something."""
    session.clear()
    return redirect(url_for("accounts.login_page"))


def log_in(user_id):
    """Start a fresh session that remembers who is logged in."""
    session.clear()
    session["user_id"] = user_id
