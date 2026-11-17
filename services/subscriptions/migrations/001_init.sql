-- 001: the Subscriptions service's first tables (same columns as in Assignment 1, now in SQL Server).
-- Never edit this file once it has run anywhere: changes go in a new numbered file.
-- Dates are kept as text in ISO form (2026-01-15), as in Assignment 1, and money as whole cents.

CREATE TABLE users (
    id INT IDENTITY PRIMARY KEY,
    email NVARCHAR(254) NOT NULL UNIQUE,
    password_hash NVARCHAR(255) NOT NULL,
    created_date NVARCHAR(10) NOT NULL
);

CREATE TABLE subscriptions (
    id INT IDENTITY PRIMARY KEY,
    user_id INT NOT NULL,
    name NVARCHAR(100) NOT NULL,
    category NVARCHAR(50) NOT NULL,
    price_cents INT NOT NULL CHECK (price_cents >= 0),
    billing_cycle NVARCHAR(10) NOT NULL
        CHECK (billing_cycle IN ('weekly', 'monthly', 'quarterly', 'yearly')),
    first_payment_date NVARCHAR(10) NOT NULL,
    is_trial BIT NOT NULL DEFAULT 0,
    last_used_date NVARCHAR(10) NULL,
    status NVARCHAR(10) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'cancelled')),
    cancelled_date NVARCHAR(10) NULL
);

CREATE TABLE price_changes (
    id INT IDENTITY PRIMARY KEY,
    subscription_id INT NOT NULL REFERENCES subscriptions (id),
    old_price_cents INT NOT NULL,
    new_price_cents INT NOT NULL,
    changed_date NVARCHAR(10) NOT NULL
);
