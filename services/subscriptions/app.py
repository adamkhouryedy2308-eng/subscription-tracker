"""The Subscriptions service: accounts and subscriptions, answering in JSON."""
import os
from datetime import date

from flask import Flask, jsonify
from flask.json.provider import DefaultJSONProvider

import db
from accounts import repository as accounts_repository
from accounts.routes import bp as accounts_endpoints
from subscriptions import repository as subscriptions_repository
from subscriptions.routes import bp as subscriptions_endpoints


class JSONWithDates(DefaultJSONProvider):
    """JSON has no date type, so dates are sent as text like "2026-01-15"."""

    @staticmethod
    def default(value):
        if isinstance(value, date):
            return value.isoformat()
        return DefaultJSONProvider.default(value)


def get_secret_key():
    """The key that stamps login tokens. It comes from an environment variable, never from Git."""
    key = os.environ.get("SECRET_KEY")
    if not key:
        raise RuntimeError("Set the SECRET_KEY environment variable before starting the service.")
    return key


def create_app():
    """Build the Flask app and make sure the database is ready."""
    app = Flask(__name__)
    app.json = JSONWithDates(app)
    app.config["SECRET_KEY"] = get_secret_key()
    # Uploaded bank statements may be at most 1 MB; bigger files get "413 Too Large".
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

    db.init_db([
        accounts_repository.CREATE_TABLE,
        subscriptions_repository.CREATE_TABLE,
        subscriptions_repository.CREATE_PRICE_CHANGES_TABLE,
    ])

    app.register_blueprint(accounts_endpoints)
    app.register_blueprint(subscriptions_endpoints)

    # Errors are JSON too, so the pages can always read the answer.
    @app.errorhandler(404)
    def not_found(error):
        return jsonify(error="Not found."), 404

    @app.errorhandler(405)
    def wrong_method(error):
        return jsonify(error="This method is not allowed here."), 405

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(errors=["The file is too large. The limit is 1 MB."]), 413

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    create_app().run(host="0.0.0.0", port=port)
