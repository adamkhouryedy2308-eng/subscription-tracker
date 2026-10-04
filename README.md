# SubTrack – Subscription Tracker

A simple web app that helps people keep track of their recurring subscriptions
(Netflix, Spotify, gym, iCloud, …), see how much they really spend, and get
warned before a renewal or a free trial turns into a charge.

Built for **Software Development & DevOps – Individual Assignment 1**
(Python + Flask + SQLite, single process).

## Run it

You need **Python 3.10 or newer**. From the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate          # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:8000**, create an account and start adding
subscriptions.

- `python app.py` is the one command that starts the app. It listens on
  `0.0.0.0`, so it can also be reached from outside a container later.
- **`PORT`** sets the port (default `8000`), e.g. `PORT=8080 python app.py`.
- **`DATA_DIR`** sets the folder for the SQLite database (default `./data`).
- No manual setup: the tables and the key that signs the login cookie are
  created automatically on the first start, inside `DATA_DIR`.
- `requirements.txt` is the only manifest. It lists every package with an
  exact version.

**To try the bank import**, open *Import from bank* and upload
`sample_data/bank_statement_example.csv`: six months of made-up payments in
which SubTrack finds six subscriptions.

## Run the tests

```bash
pytest
pytest --cov=subscriptions --cov=budgets --cov=accounts --cov=db --cov-report=term-missing
```

The first command runs all 170 tests. The second also shows the test
coverage of each file (currently 100% of the core logic; the brief asks for
at least 70%).

## The problem

Subscriptions are cheap one by one, but they add up and are easy to forget.
Free trials silently become paid plans and prices go up without anyone
noticing. Most people cannot say how much they spend per month on
subscriptions.

## Stakeholders (invented to guide design decisions)

- **Students** – main users; tight budgets, many small subscriptions.
- **IE Student Union** – wants to offer the tool to ~5,000 students as part of
  a financial-wellbeing campaign, so many people share one app and each
  person's data must stay private.
- **Me (developer)** – has to maintain the app and later split it into
  services and deploy it to Azure (Assignment 2).

## What SubTrack does

### Domain 1 – Subscriptions (`subscriptions/`)

- Add, edit and cancel subscriptions: name, one of 10 fixed categories (such as
  Entertainment, AI Tools, Health & Fitness), price, billing cycle (weekly,
  monthly, quarterly, yearly), first payment date, free trial and last used date.
- The list shows the monthly and yearly total, the next payment and a countdown
  ("in 2 days") for each subscription.
- Cancelled subscriptions are kept (not deleted) and show how much cancelling
  them saves per year.
- **Price history:** every price change is saved, the list shows "▲ 19%" since
  you subscribed, and the edit page shows the history (ADR-3).
- **Bank statement import:** upload a CSV export from your bank and SubTrack
  finds the payments that repeat with a regular rhythm and a similar amount,
  then suggests them as subscriptions. The file and its payments are never
  stored; only the subscriptions you confirm are saved (ADR-5).

### Domain 2 – Budgets & Alerts (`budgets/`)

- **Spending calculator:** what each category costs per month and per year,
  and its share of the total.
- **Budgets:** a monthly budget per category with a green, amber (80% or more)
  or red (over) bar. Only the limits are stored; spending is worked out live
  (ADR-3).
- **Alerts** with a counter in the sidebar: free trial ending (7 days), over
  budget, price went up (last 30 days), payment soon (3 days) and not used for
  30 days.

### Accounts (`accounts/`)

A supporting part, not a third feature domain: sign up, log in and log out.
Passwords are stored only as a salted hash, every page except log in and sign
up needs a login, and each user only sees their own data (`user_id` in
every query, ADR-3).

## How the parts fit together

| Part | Owns | Talks to the others through |
|---|---|---|
| Subscriptions | `subscriptions`, `price_changes` tables | `get_active_subscriptions(user_id, today)`, the one public function |
| Budgets & Alerts | `budgets` table | only calls `get_active_subscriptions()` and reads the category list; never queries the subscriptions tables (ADR-2) |
| Accounts | `users` table | the logged-in `user_id` in the session |

Each part has the same layers: `repository.py` (all SQL for its own tables),
`service.py` (rules and calculations, no HTML) and `routes.py` (the web pages).
`db.py` only opens connections and creates the tables each part hands in.
Because Budgets & Alerts reads subscriptions through one function, the app can
later be split into two services by turning that function into an HTTP call.

```
app.py            starts Flask, creates the tables, registers each part's pages
db.py             SQLite connection (DATA_DIR) and table creation
accounts/         users, password hashing, log in / sign up / log out
subscriptions/    subscriptions, price history, bank import
budgets/          budgets, spending calculator, alerts
templates/        HTML pages (Jinja)
static/style.css  the design, including dark mode and a phone layout
sample_data/      a made-up bank statement to try the import
tests/            unit and page tests (pytest)
```

## Decisions and AI use

- **[ADR.md](ADR.md)** – the five architecture decisions the brief asks for
  (framework, domains, data model, testing, and one thing not built), each
  with its context, alternatives and consequences.
- **[AI_USAGE.md](AI_USAGE.md)** – every use of AI (Claude Code), whether it
  was accepted or changed, and an explanation in my own words.

## How the work is organised in Git

- `main` always holds working, tested code.
- Each feature is built on its own short-lived branch and merged into `main`
  through a pull request once all tests pass: `feature/login` (#1),
  `feature/private-subscription` (#2), `feature/budgets` (#3),
  `feature/alerts` (#4), `feature/price-history` (#5),
  `feature/bank-import` (#6) and `docs/readme` for this file.
- Pull requests are merged with **Create a merge commit**, so every commit made
  on a branch stays in the history of `main`.
- Until 2026-09-30 commits went straight to `main`; from the login feature on
  (2026-10-01), every change uses its own branch.

## Scope decisions

After the professor's feedback (2026-09-29) that the first idea was "a bit
simple", three upgrades were chosen, each tied to a real user problem: the
bank statement import (people cannot type in what they have forgotten), the
alerts engine with price history (price rises and trials go unnoticed) and
the spending calculator with budgets. Login was first left out and then added
on 2026-10-01, because the Student Union scenario means many users share one
app. It uses Werkzeug's salted password hashing (which comes with Flask) and
Flask's signed session cookie. The Flask-Login extension was rejected because
it adds a package for about ten lines of code, and "Sign in with Google"
because it needs keys set up by hand, which would break the one-command setup.

Considered and **not built**:

- A machine-learning model that suggests categories: a fixed list of
  categories plus a list of known services already keeps categories
  consistent, so the model would add a large library without solving a real
  problem.
- Charts, a 12-month forecast and a timeline of upcoming charges: the budget
  bars, totals and alerts already answer "how much do I spend and what is
  coming", so these were left for later to keep the scope finishable.
- Password reset, email checks and connecting directly to a bank: each needs
  outside services or keys, which would break the one-command setup.

## SMART goals

1. **Specific:** A user can add a subscription and see its monthly cost. ✅
2. **Measurable:** Unit tests cover at least **70%** of the core business logic
   of both domains (now 100%), and the bank import finds every recurring
   payment in the sample statement with no false matches (a test checks
   exactly six). ✅
3. **Achievable:** Use only Python, Flask and SQLite (≤ 5 direct third-party
   packages; the app uses 4) so I can explain every line. ✅
4. **Relevant:** The app shows total monthly spending, any category that is
   over budget, and active alerts. ✅
5. **Time-bound:** Both domains working, tested and documented by
   **2026-10-04**. ✅
