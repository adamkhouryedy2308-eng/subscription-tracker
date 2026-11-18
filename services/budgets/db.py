"""The only file that talks to SQL Server directly: connecting, retrying, running SQL and migrations.

The repositories use query(), query_one(), execute() and insert(), so they never
open or close connections themselves.
"""
import os
import time
from urllib.parse import unquote, urlparse

import pymssql

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")


def connect():
    """Open a connection using DATABASE_URL, e.g. mssql://user:password@localhost:1433/subscriptions.

    Rows come back as dicts, so columns are read by name: row["email"].
    """
    url = urlparse(os.environ["DATABASE_URL"])
    return pymssql.connect(
        server=url.hostname,
        port=url.port or 1433,
        user=unquote(url.username),
        password=unquote(url.password),
        database=url.path.lstrip("/"),
        login_timeout=5,
        timeout=10,
        as_dict=True,
    )


def connect_with_retry(attempts=20):
    """Connect, trying again while the database is not ready yet.

    SQL Server in compose needs about 20 s to start, and Azure SQL serverless can
    need about a minute to resume from pause. Each wait is a bit longer than the
    last (1 s, 2 s, ... up to 5 s): about a minute and a half in total.
    """
    for attempt in range(1, attempts + 1):
        try:
            return connect()
        except pymssql.Error as error:
            if attempt == attempts:
                raise
            print(f"database not ready ({attempt}/{attempts}): {error}", flush=True)
            time.sleep(min(attempt, 5))


def query(sql, params=()):
    """Run a SELECT and return every row as a dict."""
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()


def query_one(sql, params=()):
    """Run a SELECT and return the first row as a dict, or None if there is none."""
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    """Run an INSERT, UPDATE or DELETE and save it (commit)."""
    with connect() as conn:
        conn.cursor().execute(sql, params)
        conn.commit()


def insert(sql, params=()):
    """Run an INSERT that ends with OUTPUT INSERTED.id and return the new row's id."""
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        new_id = cursor.fetchone()["id"]
        conn.commit()
        return new_id


def database_works():
    """True if this service can write to and read from its own database (used by GET /health).

    It writes the current time into the one row of health_check (migration 002)
    and reads it back. Any database error means "not working", never a crash.
    """
    try:
        with connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE health_check SET checked_at = SYSUTCDATETIME() WHERE id = 1")
            cursor.execute("SELECT checked_at FROM health_check WHERE id = 1")
            row = cursor.fetchone()
            conn.commit()
        return row is not None
    except pymssql.Error:
        return False


def run_migrations(folder=MIGRATIONS_DIR):
    """Apply the numbered .sql files in `folder` that have not run yet, in order, each exactly once.

    The table schema_migrations remembers which files already ran, so a second
    start applies nothing. Each file and its line in schema_migrations are saved
    together (one commit), so a file that fails leaves no trace and stops the
    service from starting. Returns the names of the files applied now.
    """
    conn = connect_with_retry()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            IF OBJECT_ID('schema_migrations', 'U') IS NULL
                CREATE TABLE schema_migrations (
                    version NVARCHAR(255) PRIMARY KEY,
                    applied_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
                )
        """)
        conn.commit()
        cursor.execute("SELECT version FROM schema_migrations")
        already_applied = {row["version"] for row in cursor.fetchall()}

        applied_now = []
        for filename in sorted(os.listdir(folder)):
            if not filename.endswith(".sql") or filename in already_applied:
                continue
            with open(os.path.join(folder, filename)) as file:
                sql = file.read()
            for batch in split_batches(sql):
                cursor.execute(batch)
            cursor.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (filename,))
            conn.commit()
            print(f"applied migration {filename}", flush=True)
            applied_now.append(filename)

    if not applied_now:
        print("database schema up to date, no migrations to apply", flush=True)
    return applied_now


def split_batches(sql):
    """Split a migration file on lines that say GO.

    SQL Server needs separate batches when a later statement uses something an
    earlier one created, e.g. a new column that is then filled in.
    """
    batches = []
    current = []
    for line in sql.splitlines():
        if line.strip().upper() == "GO":
            batches.append("\n".join(current))
            current = []
        else:
            current.append(line)
    batches.append("\n".join(current))
    return [batch for batch in batches if batch.strip()]
