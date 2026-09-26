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
| **1. Subscriptions** | Add, edit, cancel and list subscriptions (name, category, price, billing cycle, next payment date, free-trial end date) | `subscriptions` table |
| **2. Budgets & Alerts** | Set a monthly budget per category, compare real spending against it, and warn about upcoming renewals and ending trials | `budgets` table |

Budgets & Alerts only reads subscription data through one function exposed by
the Subscriptions domain – it never queries the `subscriptions` table directly.
That function is the "seam" where the app could later be split into two services.

## SMART goals

1. **Specific:** A user can add a subscription and see its monthly cost on the dashboard.
2. **Measurable:** Unit tests cover at least **70%** of the core business logic of both domains.
3. **Achievable:** Use only Python, Flask and SQLite (≤ 5 third-party packages) so I can explain every line.
4. **Relevant:** The dashboard shows total monthly spending and any category that is over budget.
5. **Time-bound:** Both domains working, tested and documented by **2026-10-04**.

## Status

🚧 Planning phase – setup instructions will be added as the app is built.
