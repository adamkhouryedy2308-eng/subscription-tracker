# Architecture Decision Records

## 1. Backend language and framework: Python with Flask
Date: 2026-09-27
Status: Decided
Context: SubTrack needs a small web backend that serves HTML pages, stores data in SQLite and runs as one process, and I have to be able to explain all of it on paper. Python is the language I am most comfortable in.
Decision: Use Python with Flask and the built-in `sqlite3` module, with HTML pages rendered by Flask's Jinja templates.
Alternatives considered: Django was rejected because its ORM, admin panel and user system are far more than two small domains need, and it would hide how the SQL works. FastAPI was rejected because it is built for JSON APIs, while SubTrack mainly shows HTML pages to a user. Python's built-in `http.server` was rejected because I would have to write routing and form handling by hand.
Consequences: Flask keeps the project to one third-party package and each route is a plain function I can read. The cost is that I write SQL and input validation myself, which Django would have done for me.

## 2. Two independent domains with one public function between them
Date: 2026-09-29
Status: Decided
Context: The brief needs two feature domains that could later become separate services. Budgets & Alerts needs subscription data (costs, categories, payment dates) to compare against budgets and raise alerts, so the two domains must share data without depending on each other's internals.
Decision: Each domain lives in its own package (`subscriptions/` now, `budgets/` later) with its own table, SQL, rules and pages. Budgets & Alerts reads subscription data only by calling `subscriptions.service.get_active_subscriptions()`, which returns plain dictionaries, and never queries the `subscriptions` table.
Alternatives considered: Letting Budgets & Alerts query the `subscriptions` table directly with a SQL JOIN was rejected: it is less code today, but both domains would depend on the same table layout, so splitting them into services would mean rewriting Budgets & Alerts. One shared `models.py` holding both domains' code was rejected for the same reason and because it would mix two responsibilities in one file.
Consequences: In Assignment 2 only `get_active_subscriptions()` has to change, into an HTTP call to the Subscriptions service. The cost is that Budgets & Alerts cannot JOIN the two tables and has to match categories in Python instead.
