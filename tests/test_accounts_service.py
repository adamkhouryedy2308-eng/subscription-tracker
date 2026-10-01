from datetime import date

from accounts import service

TODAY = date(2026, 10, 1)


def sign_up_form(email="Ana@Example.com ", password="secret-pass", confirm=None):
    """A sign-up form that passes validation unless a test changes it."""
    return {
        "email": email,
        "password": password,
        "confirm_password": password if confirm is None else confirm,
    }


# --- Checking the sign-up form ---------------------------------------------------

def test_valid_sign_up_has_no_errors_and_a_clean_email():
    email, errors = service.validate_registration(sign_up_form())
    assert errors == []
    assert email == "ana@example.com"


def test_sign_up_with_every_mistake_lists_every_error():
    email, errors = service.validate_registration(sign_up_form("not-an-email", "short", "other"))
    assert errors == [
        "Enter a valid email, like name@example.com.",
        "Password must be at least 8 characters.",
        "The two passwords do not match.",
    ]


def test_email_needs_a_name_and_a_domain_with_a_dot():
    for bad_email in ["@example.com", "ana@", "ana@example", ""]:
        email, errors = service.validate_registration(sign_up_form(bad_email))
        assert "Enter a valid email, like name@example.com." in errors


# --- Creating accounts -------------------------------------------------------

def test_register_saves_a_hash_and_never_the_password(temp_db):
    user_id, errors = service.register(sign_up_form(), TODAY)
    assert errors == []
    user = service.get_user(user_id)
    assert user["email"] == "ana@example.com"
    assert user["password_hash"] != "secret-pass"
    assert "secret-pass" not in user["password_hash"]
    assert user["created_date"] == "2026-10-01"


def test_register_with_errors_saves_nothing(temp_db):
    user_id, errors = service.register(sign_up_form(password="short"), TODAY)
    assert user_id is None
    assert service.check_login({"email": "ana@example.com", "password": "short"}) is None


def test_the_same_email_cannot_register_twice(temp_db):
    service.register(sign_up_form(), TODAY)
    user_id, errors = service.register(sign_up_form("ANA@example.com"), TODAY)
    assert user_id is None
    assert errors == ["An account with this email already exists. Log in instead."]


# --- Logging in ----------------------------------------------------------------

def test_login_with_the_right_password_gives_the_user_id(temp_db):
    user_id, errors = service.register(sign_up_form(), TODAY)
    assert service.check_login({"email": " ANA@example.com", "password": "secret-pass"}) == user_id


def test_login_with_a_wrong_password_or_unknown_email_fails(temp_db):
    service.register(sign_up_form(), TODAY)
    assert service.check_login({"email": "ana@example.com", "password": "wrong-pass"}) is None
    assert service.check_login({"email": "nobody@example.com", "password": "secret-pass"}) is None
    assert service.check_login({}) is None


def test_get_user_for_a_missing_id_is_none(temp_db):
    assert service.get_user(99) is None
