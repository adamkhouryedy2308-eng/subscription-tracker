import os

from flask import Flask

import db


def create_app():
    """Build the Flask app and make sure the database is ready."""
    app = Flask(__name__)

    # Each feature domain will add its own table here (none yet).
    db.init_db([])

    @app.route("/")
    def home():
        return "SubTrack is running"

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    create_app().run(host="0.0.0.0", port=port)
