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

## 3. Simple login with hashed passwords, and every subscription belongs to one user
Date: 2026-10-01
Status: Decided (replaces my earlier plan to build no login)
Context: The IE Student Union wants to offer SubTrack to about 5,000 students, so many people will use the same app, and what someone pays for is private financial information. Without accounts everyone would see and change one shared list. I first planned to leave login out to keep the app small, but then the app only works for one person.
Decision: Add a small `accounts/` package with its own `users` table (email, password hash, created date). Passwords are hashed with Werkzeug's `generate_password_hash`, which comes with Flask, and checked with `check_password_hash`; the password itself is never stored. After logging in, Flask's signed session cookie remembers the `user_id`. One function that runs before every request sends anyone who is not logged in to the login page, so every new page is protected without extra code. Each subscription gets a `user_id` column and every SQL query filters by it. `user_id` is a plain column with no FOREIGN KEY to `users`, so the Subscriptions domain does not depend on the accounts table, for the same reason as ADR-2.
Alternatives considered: The Flask-Login extension was rejected because it adds a package for what is about ten lines here and hides how the session works. Django's user system was already rejected in ADR-1. "Sign in with Google" was rejected because it needs the app registered with Google and secret keys set up by hand, which breaks the "no manual setup" rule. Saving passwords as plain text or with a fast hash like SHA-256 was rejected: anyone who got the database file could read or quickly guess the passwords, while Werkzeug's scrypt hash is salted and slow on purpose.
Consequences: Each user only sees their own subscriptions, and tests show that another user's subscription returns "not found". Logging out only works with POST, and the cookie is set to SameSite=Lax, so another website cannot log a user out or submit forms for them. The cost is that every subscription function now needs a `user_id`, and there is no password reset or email check yet. The key that signs the cookie is created automatically in `DATA_DIR` on the first start, so setup stays one command; in Assignment 2 it should come from an environment variable instead.
