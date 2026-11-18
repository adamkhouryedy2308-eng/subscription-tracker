-- 002: a one-row table that GET /health writes the time into and reads back,
-- to prove this service can still write to and read from its own database.
-- It holds no user data, so it is safe to create on a database that already has data.

CREATE TABLE health_check (
    id INT PRIMARY KEY CHECK (id = 1),          -- only ever one row
    checked_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

INSERT INTO health_check (id) VALUES (1);
