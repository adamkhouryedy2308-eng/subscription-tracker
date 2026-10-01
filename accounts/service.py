"""Rules for accounts: checking sign-up forms, hashing passwords and checking logins."""
from werkzeug.security import check_password_hash, generate_password_hash

from accounts import repository

MIN_PASSWORD_LENGTH = 8


def clean_email(text):
    """Emails are compared without spaces and in lowercase: Ana@IE.edu is ana@ie.edu."""
    return text.strip().lower()


def validate_registration(form):
    """Check a sign-up form. Return (email, errors)."""
    errors = []
    email = clean_email(form.get("email", ""))
    password = form.get("password", "")

    name, at, domain = email.partition("@")
    if not name or not at or "." not in domain:
        errors.append("Enter a valid email, like name@example.com.")
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if password != form.get("confirm_password", ""):
        errors.append("The two passwords do not match.")
    return email, errors


def register(form, today):
    """Create an account. Return (new_user_id, errors).

    Only a hash of the password is saved, never the password itself.
    """
    email, errors = validate_registration(form)
    if errors:
        return None, errors
    if repository.get_user_by_email(email) is not None:
        return None, ["An account with this email already exists. Log in instead."]
    password_hash = generate_password_hash(form["password"])
    return repository.add_user(email, password_hash, today.isoformat()), []


def check_login(form):
    """Return the user's id if the email and password match, otherwise None.

    A wrong email and a wrong password give the same answer, so nobody can
    find out which emails have an account.
    """
    user = repository.get_user_by_email(clean_email(form.get("email", "")))
    if user is None:
        return None
    if not check_password_hash(user["password_hash"], form.get("password", "")):
        return None
    return user["id"]


def get_user(user_id):
    """One user, or None if the id does not exist."""
    return repository.get_user(user_id)
