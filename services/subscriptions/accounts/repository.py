"""SQL for the users table. Only this file reads or writes that table (created in migrations/001_init.sql)."""
import db


def add_user(email, password_hash, created_date):
    """Save a new user and return their id."""
    return db.insert(
        "INSERT INTO users (email, password_hash, created_date) OUTPUT INSERTED.id VALUES (%s, %s, %s)",
        (email, password_hash, created_date),
    )


def get_user_by_email(email):
    """Return one user as a dict, or None if no account uses this email."""
    return db.query_one("SELECT * FROM users WHERE email = %s", (email,))


def get_user(user_id):
    """Return one user as a dict, or None if the id does not exist."""
    return db.query_one("SELECT * FROM users WHERE id = %s", (user_id,))
