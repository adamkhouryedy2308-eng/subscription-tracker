"""The Subscriptions service: accounts and subscriptions, answering in JSON."""
import os
import time
from datetime import date

from flask import Flask, g, jsonify, request
from flask.json.provider import DefaultJSONProvider

import db
from accounts.routes import bp as accounts_endpoints
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
    """Build the Flask app and bring the database up to date (migrations) before serving."""
    app = Flask(__name__)
    app.json = JSONWithDates(app)
    app.config["SECRET_KEY"] = get_secret_key()
    # Uploaded bank statements may be at most 1 MB; bigger files get "413 Too Large".
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

    db.run_migrations()

    # One log line per request on stdout, e.g. "GET /budgets 200 12.3ms".
    # Only the method and path are logged: never tokens, passwords or data.
    @app.before_request
    def start_timer():
        g.started = time.perf_counter()

    @app.after_request
    def log_request(response):
        duration_ms = (time.perf_counter() - g.get("started", time.perf_counter())) * 1000
        print(f"{request.method} {request.path} {response.status_code} {duration_ms:.1f}ms", flush=True)
        return response

    @app.route("/health")
    def health():
        """Is THIS service working? 200 if it can use its own database, 503 if not.

        It does not check the other service: each service reports only its own health.
        GIT_SHA is set when the Docker image is built, so we can see which version runs.
        """
        version = os.environ.get("GIT_SHA", "dev")
        if db.database_works():
            return jsonify(status="ok", db="ok", version=version)
        return jsonify(status="error", db="unavailable", version=version), 503

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
