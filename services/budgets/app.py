"""The Budgets & Alerts service: budgets and alerts, answering in JSON."""
import os
from datetime import date

from flask import Flask, jsonify
from flask.json.provider import DefaultJSONProvider

import db
from budgets import repository as budgets_repository
from budgets.routes import bp as budgets_endpoints


class JSONWithDates(DefaultJSONProvider):
    """JSON has no date type, so dates are sent as text like "2026-01-15"."""

    @staticmethod
    def default(value):
        if isinstance(value, date):
            return value.isoformat()
        return DefaultJSONProvider.default(value)


def get_secret_key():
    """The key that checks login tokens: the same one the Subscriptions service stamps them with."""
    key = os.environ.get("SECRET_KEY")
    if not key:
        raise RuntimeError("Set the SECRET_KEY environment variable before starting the service.")
    return key


def create_app():
    """Build the Flask app and make sure the database is ready."""
    app = Flask(__name__)
    app.json = JSONWithDates(app)
    app.config["SECRET_KEY"] = get_secret_key()

    db.init_db([budgets_repository.CREATE_TABLE])
    app.register_blueprint(budgets_endpoints)

    # Errors are JSON too, so the pages can always read the answer.
    @app.errorhandler(404)
    def not_found(error):
        return jsonify(error="Not found."), 404

    @app.errorhandler(405)
    def wrong_method(error):
        return jsonify(error="This method is not allowed here."), 405

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    create_app().run(host="0.0.0.0", port=port)
