# SubTrack – Subscription Tracker

A simple web app that helps people keep track of their recurring subscriptions
(Netflix, Spotify, gym, iCloud, …), see how much they really spend, and get
warned before a renewal or a free trial turns into a charge.

Built for **Software Development & DevOps – Individual Assignment 1**
(Python + Flask + SQLite, single process).

## The problem

Subscriptions are cheap one by one, but they add up and are easy to forget.
Free trials silently become paid plans. Most people cannot say how much they
spend per month on subscriptions.

## Stakeholders (invented to guide design decisions)

- **Students** – main users; tight budgets, many small subscriptions.
- **IE Student Union** – wants to offer the tool to ~5,000 students as part of
  a financial-wellbeing campaign.
- **Me (developer)** – has to maintain the app and later split it into
  services and deploy it to Azure (Assignment 2).

## Feature domains

| Domain | Responsibility | Owns data |
|---|---|---|
| **1. Subscriptions** | Add, edit, cancel and list subscriptions (name, category, price, billing cycle, next payment date, free trial, last used date), keep a history of price changes, and import a bank statement (CSV) to find recurring payments automatically | `subscriptions`, `price_changes` tables |
| **2. Budgets & Alerts** | A spending calculator (monthly and yearly totals, split by category such as Entertainment, AI Tools, Health & Fitness), a monthly budget per category compared against real spending, an alerts engine (renewal soon, trial ending, over budget, unused, price rise) and a dashboard with charts | `budgets` table |

Budgets & Alerts only reads subscription data through one function exposed by
the Subscriptions domain – it never queries the `subscriptions` table directly.
That function is the "seam" where the app could later be split into two services.

### Accounts (login)

Accounts is a supporting part, not a third feature domain: people sign up with
an email and password, log in and log out. Passwords are stored only as a hash,
every page except log in and sign up needs a login, and each user only sees
their own subscriptions. See ADR-3.

## Scope update after professor feedback (2026-09-29)

The professor approved the idea but called it "a bit simple". To add depth
without adding complexity for its own sake, three upgrades were chosen, each
tied to a real user problem:

- **Bank statement import with recurring-payment detection:** people cannot
  type in a subscription they have forgotten about. The user uploads the CSV
  export from their bank, and SubTrack finds the payments that repeat at a
  regular interval with a similar amount, then suggests them as subscriptions.
  The file is processed inside the app and never sent anywhere, and the
  transactions are not stored: only the subscriptions the user confirms are
  saved. The first upload should cover about 6 months (at least 3), so monthly
  subscriptions appear several times; a refresh of the last 3 months about once
  a month catches new subscriptions and price rises.
- **Smart alerts engine:** renewal soon, free trial ending, over budget, unused
  for 30+ days, and price rises, backed by a price-change history.
- **Spending calculator and dashboard:** every plan converted to the same
  monthly and yearly scale, totals split by category, charts for spending by
  category, budgets and a 12-month forecast, plus a timeline of upcoming charges.

A machine-learning model that suggests categories was considered and rejected:
a fixed list of categories plus a list of known services already keeps
categories consistent, so the model would add a large library without solving
a real problem.

## SMART goals

1. **Specific:** A user can add a subscription and see its monthly cost on the dashboard.
2. **Measurable:** Unit tests cover at least **70%** of the core business logic of both domains, and the bank import finds every recurring payment in the sample statements with no false matches.
3. **Achievable:** Use only Python, Flask and SQLite (≤ 5 direct third-party packages) so I can explain every line.
4. **Relevant:** The dashboard shows total monthly spending, any category that is over budget, and active alerts.
5. **Time-bound:** Both domains working, tested and documented by **2026-10-04**.

## How the work is organised in Git

- `main` always holds working, tested code.
- Each feature is built on its own short-lived branch named `feature/<name>`
  (for example `feature/login`), pushed to GitHub and merged into `main`
  through a pull request once all tests pass.
- Pull requests are merged with **Create a merge commit**, so every commit made
  on the branch stays in the history of `main`.
- Until 2026-09-30 commits went straight to `main`; from the login feature on
  (2026-10-01), every feature uses its own branch.

## Status

🚧 In development – setup instructions will be added as the app is built.
