# Architecture Decision Records

## 1. Backend language and framework: Python with Flask
Date: 2026-09-27
Status: Decided
Context: SubTrack needs a small web backend that serves HTML pages, stores data in SQLite and runs as one process, and I have to be able to explain all of it on paper. Python is the language I am most comfortable in.
Decision: Use Python with Flask and the built-in `sqlite3` module, with HTML pages rendered by Flask's Jinja templates.
Alternatives considered: Django was rejected because its ORM, admin panel and user system are far more than two small domains need, and it would hide how the SQL works. FastAPI was rejected because it is built for JSON APIs, while SubTrack mainly shows HTML pages to a user. Python's built-in `http.server` was rejected because I would have to write routing and form handling by hand.
Consequences: Flask keeps the project to one third-party package and each route is a plain function I can read. The cost is that I write SQL and input validation myself, which Django would have done for me.
