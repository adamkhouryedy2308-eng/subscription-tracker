import os

from flask import Flask

import db
from subscriptions import repository as subscriptions_repository


def create_app():
    """Build the Flask app and make sure the database is ready."""
    app = Flask(__name__)

    # Each feature domain hands in its own table; db.py never changes.
    db.init_db([subscriptions_repository.CREATE_TABLE])

    @app.route("/")
    def home():
        return "SubTrack is running"

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    create_app().run(host="0.0.0.0", port=port)
