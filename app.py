import os

from flask import Flask, redirect, url_for

import db
from subscriptions import repository as subscriptions_repository
from subscriptions.routes import bp as subscriptions_pages


def create_app():
    """Build the Flask app and make sure the database is ready."""
    app = Flask(__name__)

    # Each feature domain hands in its own table; db.py never changes.
    db.init_db([subscriptions_repository.CREATE_TABLE])

    # Each feature domain brings its own group of pages (a Blueprint).
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
