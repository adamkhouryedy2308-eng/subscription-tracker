-- 001: the Budgets & Alerts service's first table (same columns as in Assignment 1, now in SQL Server).
-- Never edit this file once it has run anywhere: changes go in a new numbered file.
-- user_id is a plain number: the users live in the Subscriptions service's database (no foreign key across the seam).

CREATE TABLE budgets (
    id INT IDENTITY PRIMARY KEY,
    user_id INT NOT NULL,
    category NVARCHAR(50) NOT NULL,
    monthly_limit_cents INT NOT NULL CHECK (monthly_limit_cents > 0),
    UNIQUE (user_id, category)
);
