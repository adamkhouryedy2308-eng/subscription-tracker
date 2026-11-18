-- Creates the databases and one login per service. Run by the one-off db-init job in docker-compose.yml.
-- Idempotent: every line first checks if the thing already exists, so it is safe on every `docker compose up`.
-- The passwords come in as sqlcmd variables: $(SUBSCRIPTIONS_DB_PASSWORD) and $(BUDGETS_DB_PASSWORD).
-- The *_test databases are empty copies the tests use, so tests never touch your real data.

IF DB_ID('subscriptions') IS NULL CREATE DATABASE subscriptions;
IF DB_ID('subscriptions_test') IS NULL CREATE DATABASE subscriptions_test;
IF DB_ID('budgets') IS NULL CREATE DATABASE budgets;
IF DB_ID('budgets_test') IS NULL CREATE DATABASE budgets_test;
GO

-- If a login already exists, its password is set again from .env, so changing a
-- password in .env only needs another `docker compose up`.
IF SUSER_ID('subscriptions_user') IS NULL
    CREATE LOGIN subscriptions_user WITH PASSWORD = '$(SUBSCRIPTIONS_DB_PASSWORD)', CHECK_POLICY = OFF;
ELSE
    ALTER LOGIN subscriptions_user WITH PASSWORD = '$(SUBSCRIPTIONS_DB_PASSWORD)';
IF SUSER_ID('budgets_user') IS NULL
    CREATE LOGIN budgets_user WITH PASSWORD = '$(BUDGETS_DB_PASSWORD)', CHECK_POLICY = OFF;
ELSE
    ALTER LOGIN budgets_user WITH PASSWORD = '$(BUDGETS_DB_PASSWORD)';
GO

-- Each login becomes a user in ITS OWN databases only, with the rights to read, write
-- and change tables (db_ddladmin, needed for migrations). It has no user in the other
-- service's databases, so it cannot open them.
USE subscriptions;
GO
IF USER_ID('subscriptions_user') IS NULL CREATE USER subscriptions_user FOR LOGIN subscriptions_user;
ALTER ROLE db_ddladmin ADD MEMBER subscriptions_user;
ALTER ROLE db_datareader ADD MEMBER subscriptions_user;
ALTER ROLE db_datawriter ADD MEMBER subscriptions_user;
GO
USE subscriptions_test;
GO
IF USER_ID('subscriptions_user') IS NULL CREATE USER subscriptions_user FOR LOGIN subscriptions_user;
ALTER ROLE db_ddladmin ADD MEMBER subscriptions_user;
ALTER ROLE db_datareader ADD MEMBER subscriptions_user;
ALTER ROLE db_datawriter ADD MEMBER subscriptions_user;
GO

USE budgets;
GO
IF USER_ID('budgets_user') IS NULL CREATE USER budgets_user FOR LOGIN budgets_user;
ALTER ROLE db_ddladmin ADD MEMBER budgets_user;
ALTER ROLE db_datareader ADD MEMBER budgets_user;
ALTER ROLE db_datawriter ADD MEMBER budgets_user;
GO
USE budgets_test;
GO
IF USER_ID('budgets_user') IS NULL CREATE USER budgets_user FOR LOGIN budgets_user;
ALTER ROLE db_ddladmin ADD MEMBER budgets_user;
ALTER ROLE db_datareader ADD MEMBER budgets_user;
ALTER ROLE db_datawriter ADD MEMBER budgets_user;
GO
