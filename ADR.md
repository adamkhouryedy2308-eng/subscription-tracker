# Architecture Decision Records

## 1. Backend language and framework: Python with Flask
Date: 2026-09-27
Status: Decided
Context: SubTrack needs a small web backend that serves HTML pages, stores data in SQLite and runs as one process, and I have to be able to explain all of it on paper. Python is the language I am most comfortable in.
Decision: Use Python with Flask and the built-in `sqlite3` module, with HTML pages rendered by Flask's Jinja templates.
Alternatives considered: Django was rejected because its ORM, admin panel and user system are far more than two small domains need, and it would hide how the SQL works. FastAPI was rejected because it is built for JSON APIs, while SubTrack mainly shows HTML pages to a user. Python's built-in `http.server` was rejected because I would have to write routing and form handling by hand.
Consequences: Flask keeps the app to Flask and the Werkzeug library that comes with it, and each route is a plain function I can read. The cost is that I write SQL and input validation myself, which Django would have done for me.

## 2. Two independent domains with one public function between them
Date: 2026-09-29
Status: Decided
Context: The brief needs two feature domains that could later become separate services. Budgets & Alerts needs subscription data (costs, categories, payment dates) to compare against budgets and raise alerts, so the two domains must share data without depending on each other's internals.
Decision: Each domain lives in its own package (`subscriptions/` now, `budgets/` later) with its own table, SQL, rules and pages. Budgets & Alerts reads subscription data only by calling `subscriptions.service.get_active_subscriptions()`, which returns plain dictionaries, and never queries the `subscriptions` table.
Alternatives considered: Letting Budgets & Alerts query the `subscriptions` table directly with a SQL JOIN was rejected: it is less code today, but both domains would depend on the same table layout, so splitting them into services would mean rewriting Budgets & Alerts. One shared `models.py` holding both domains' code was rejected for the same reason and because it would mix two responsibilities in one file.
Consequences: In Assignment 2 only `get_active_subscriptions()` has to change, into an HTTP call to the Subscriptions service. The cost is that Budgets & Alerts cannot JOIN the two tables and has to match categories in Python instead.

## 3. Data model: each domain owns its tables, linked by `user_id` and one foreign key inside Subscriptions
Date: 2026-10-02
Status: Decided
Context: Budgets & Alerts needs what each category costs, but the subscriptions belong to the other domain. Since 2026-10-01 SubTrack also has login, because in the Student Union scenario many students share one app, so every row belongs to one user and must stay private. On 2026-10-03 the model was extended with a `price_changes` table for price history.
Decision: Each domain owns its tables: `users` (Accounts, with passwords stored only as a salted Werkzeug hash), `subscriptions` and `price_changes` (Subscriptions) and `budgets` (Budgets & Alerts), and the only FOREIGN KEY is `price_changes.subscription_id`, inside one domain. `budgets` stores only one monthly limit per user and category (`UNIQUE (user_id, category)`); what a category costs is never stored but worked out on every page view from `get_active_subscriptions()`.
Alternatives considered: Keeping the app without login, with one shared list, was rejected because every student would see and change everyone's subscriptions. Storing each category's spending in `budgets` was rejected because Subscriptions would then have to update Budgets on every change (a two-way dependency) and the total could go stale. Foreign keys from `subscriptions` and `budgets` to `users` were rejected so that no domain depends on another domain's table (ADR-2), and a single `original_price_cents` column instead of `price_changes` was rejected because it would lose every change in between.
Consequences: Each domain can move into its own service together with its tables, and spending is always up to date. The cost is that ownership is checked by `WHERE user_id = ?` in every query instead of by the database, and spending is recalculated on every page view.

## 4. Testing approach: unit tests on the rules first, page tests for flows and security
Date: 2026-10-04
Status: Decided
Context: The brief asks for at least 70% coverage of the core business logic of both domains. That logic (costs per billing cycle, next payment dates, budget status, alert rules, recurring-payment detection) is where a mistake would show users wrong amounts or dates.
Decision: Most tests are fast unit tests of the service functions such as `next_payment_date`, `build_report`, `build_alerts` and `find_recurring`, using plain dictionaries and fixed dates, and page tests with Flask's test client and a temporary SQLite file per test cover each flow and the security rules (login required, another user's data returns 404, GET never changes data). Coverage is measured with `pytest --cov=subscriptions --cov=budgets --cov=accounts --cov=db`.
Alternatives considered: Browser end-to-end tests with a tool like Selenium were rejected because they are slow and need a browser driver installed, which breaks the one-command setup. Mocking the database was rejected because a real temporary SQLite file also tests the SQL itself and is still fast (170 tests in under 10 seconds).
Consequences: Coverage of those packages is 100%, and edge cases such as payments on the 31st, cancelling twice and the 1 MB upload limit have their own tests. Left thinner on purpose: the look of the pages (CSS, dark mode, phone layout) and the browser-only confirm before cancelling, which I checked by hand in the app instead.

## 5. Not built: a direct connection to the user's bank
Date: 2026-10-04
Status: Decided
Context: The bank import has to see the user's payments to find forgotten subscriptions, and the smoothest experience would be to connect SubTrack straight to the bank account. Bank data is very private: it shows someone's salary, the shops they use and where they travel.
Decision: I chose not to build a bank connection: the user uploads a CSV export (at most 1 MB) that is read in memory, and only the subscriptions the user ticks are saved, never the file or its transactions.
Alternatives considered: An open-banking connection through a provider was rejected because it needs an account with that provider, secret keys and a consent flow, which breaks the "one command, no manual setup" rule and makes the app depend on an outside service. Saving every transaction to analyse it later was rejected because it would store private data the app does not need.
Consequences: Private data never reaches the database, and the import works with any bank that exports a CSV. The cost is that the user downloads and uploads the statement by hand, and only files with the columns Date, Description and Amount work.
