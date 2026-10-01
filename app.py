import os
import secrets

from flask import Flask, redirect, url_for

import db
from accounts import repository as accounts_repository
from accounts.routes import bp as accounts_pages
from subscriptions import repository as subscriptions_repository
from subscriptions.routes import bp as subscriptions_pages


def get_secret_key():
    """The key that signs the login cookie. Made once and kept in DATA_DIR, never in git."""
    path = os.path.join(os.path.dirname(db.get_db_path()), "secret_key.txt")
    if not os.path.exists(path):
        with open(path, "w") as file:
            file.write(secrets.token_hex(32))
    with open(path) as file:
        return file.read()


def create_app():
    """Build the Flask app and make sure the database is ready."""
    app = Flask(__name__)
    app.secret_key = get_secret_key()
    # The login cookie is not sent when another website submits a form to SubTrack.
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # Each part of the app hands in its own table; db.py never changes.
    db.init_db([accounts_repository.CREATE_TABLE, subscriptions_repository.CREATE_TABLE])

    # Each part of the app brings its own group of pages (a Blueprint).
    app.register_blueprint(accounts_pages)
    app.register_blueprint(subscriptions_pages)

    @app.template_filter("euros")
    def euros(cents):
        """Show cents as euros in the pages: 112139 becomes €1,121.39."""
        return f"€{cents / 100:,.2f}"

    @app.route("/")
    def home():
        return redirect(url_for("subscriptions.list_page"))

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    create_app().run(host="0.0.0.0", port=port)
