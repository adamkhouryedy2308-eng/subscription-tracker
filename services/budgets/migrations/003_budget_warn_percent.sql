-- 003: each budget gets its own warning level: "warn me when I have used X% of it".
-- Until now every budget warned at 80% (NEAR_LIMIT_PERCENT in budgets/service.py).
-- This changes a table that ALREADY HOLDS DATA without losing any row: SQL Server adds
-- the column and fills in 80 for every existing budget (the DEFAULT), so old budgets
-- behave exactly as before. Nothing is dropped or recreated.

ALTER TABLE budgets ADD warn_percent INT NOT NULL
    CONSTRAINT df_budgets_warn_percent DEFAULT 80
    CONSTRAINT ck_budgets_warn_percent CHECK (warn_percent BETWEEN 1 AND 100);
