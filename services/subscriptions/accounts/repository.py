"""SQL for the users table. Only this file reads or writes that table."""
import db

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_date TEXT NOT NULL
)
"""


def add_user(email, password_hash, created_date):
    """Save a new user and return their id."""
    conn = db.get_connection()
    cursor = conn.execute(
        "INSERT INTO users (email, password_hash, created_date) VALUES (?, ?, ?)",
        (email, password_hash, created_date),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_user_by_email(email):
    """Return one user as a dict, or None if no account uses this email."""
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user(user_id):
    """Return one user as a dict, or None if the id does not exist."""
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
