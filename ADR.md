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

## 6. The split: two services along the ADR-2 seam, with Budgets calling Subscriptions over HTTP
Date: 2026-11-16
Status: Decided
Context: Assignment 2 needs one service per feature domain, each with its own container and data, and at least one user-visible flow that crosses the seam on the server. In Assignment 1, ADR-2 put the seam at `get_active_subscriptions()`, the only way Budgets & Alerts read subscription data.
Decision: The Subscriptions service (accounts, subscriptions, price history, bank import) and the Budgets & Alerts service each answer in JSON, and the only thing that crosses the seam is one HTTP call: Budgets calls `GET /subscriptions/active` with the user's token, a 2-second timeout (`SUBSCRIPTIONS_TIMEOUT_S`) and the address from `SUBSCRIPTIONS_URL`. If that call fails, the budgets page still shows the saved budgets with a "spending unavailable" message and alerts answer a clear 503, and login stays in Subscriptions, which signs a token with `SECRET_KEY` that both services check themselves.
Alternatives considered: Letting the browser fetch both services and combine the data (client side) was rejected because the budget and alert rules, which already live and are tested in Budgets, would have to be rewritten in JavaScript without tests. Showing cached subscriptions was rejected because old data could give wrong alerts, and retrying was rejected because the user would wait longer for a call that probably still fails. Budgets asking Subscriptions to check every token was rejected because Budgets would then stop working whenever Subscriptions is down, and a separate login service was not possible because the brief allows exactly two service containers.
Consequences: ADR-2 mostly held: only that one function had to become an HTTP call, plus one hidden link, the category list, which Budgets now keeps its own copy of so that saving budgets works while Subscriptions is down. The cost is that a new category must be added in both services, and both services must be given the same `SECRET_KEY`.

## 7. Data and migrations: one SQL Server database and login per service, changed only by numbered migrations
Date: 2026-11-17
Status: Decided
Context: In Assignment 1 all four tables lived in one SQLite file and were created on first start. Assignment 2 needs one SQL Server database per service, each with its own login, and schema changes that keep the data already stored.
Decision: Subscriptions owns `users`, `subscriptions` and `price_changes` in its database and Budgets & Alerts owns `budgets` in its own, each opened only by its own login (created by `db/init.sql` locally), and each service applies the numbered files in its `migrations/` folder at startup with a small runner in `db.py` that records each file in `schema_migrations`, so every file runs once and in order. A file and its record are committed together, so a migration that fails changes nothing and the service does not start.
Alternatives considered: A migration tool such as Alembic was rejected because it adds a package and its own concepts, while our SQL is already written by hand and the runner is about 30 lines I can explain. Creating the tables with "if not exists" on every start, as in Assignment 1 and the class demo, was rejected because it cannot change a table that already holds data, and one shared database was rejected because the brief requires one database and one login per service.
Consequences: Integrity is lost at the seam: no foreign key can check `budgets.user_id`, so Budgets only trusts the user id inside a token signed by Subscriptions and filters every query by it, and the budgets of a deleted user would stay behind (the app cannot delete users). The recovery plan for a bad migration is forward-only: a failed file rolls back by itself and the previous SHA-tagged image is redeployed, the fix goes in a new numbered file because applied files are never edited, and if a migration damaged data, Azure SQL's automatic backups restore the database to a point before the deploy.
