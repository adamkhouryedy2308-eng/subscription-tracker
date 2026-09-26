# AI Usage Log

One row per meaningful AI interaction. The last column is written in my own words.

| Date/commit | Tool | Prompt | Disposition (Accepted/Modified/Rejected) | What changed & why (if modified) | In my own words, how this works |
|---|---|---|---|---|---|
| 2026-09-26 / 7253736 | Claude Code (Claude Opus 5.5) | Asked it to draft the README proposal: problem, stakeholders, the two feature domains and SMART goals | Accepted | – | The README explains that the problem is that many people rely on subscriptions in their daily lives, like apps, the gym or other services they pay for. Each one is usually cheap, but when you have many of them you lose control and start losing money without knowing what you are still paying for. The two domains are Subscriptions, which lets the user add, edit, cancel and list their subscriptions with the price, billing cycle and next payment date, and Budgets & Alerts, which lets the user set a monthly budget per category, compares it to what they actually spend, and warns them about upcoming renewals and free trials that are ending. Budgets & Alerts only reads subscriptions through one function so that the two domains stay separate, and later they can be split into two services by changing only that one function.
