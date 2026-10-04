import io
import os

from tests.test_subscriptions_pages import NETFLIX

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "sample_data", "bank_statement_example.csv")


def upload(client, content, filename="statement.csv"):
    """Send a file to the import page like a browser does."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return client.post("/subscriptions/import", data={"statement": (io.BytesIO(content), filename)},
                       content_type="multipart/form-data")


def sample_bytes():
    with open(SAMPLE, "rb") as file:
        return file.read()


def test_visitors_are_sent_to_log_in(guest):
    assert guest.get("/subscriptions/import").headers["Location"].endswith("/login")


def test_import_page_explains_that_the_file_is_not_saved(client):
    page = client.get("/subscriptions/import").get_data(as_text=True)
    assert "The file is read once and never saved." in page


def test_uploading_the_sample_shows_six_suggestions(client):
    page = upload(client, sample_bytes()).get_data(as_text=True)
    assert "Found 6 subscriptions" in page
    assert "in 61 payments" in page
    for name in ["Basic-Fit", "ChatGPT Plus", "iCloud+", "Netflix", "Padel Club Madrid", "Spotify"]:
        assert name in page
    assert "MERCADONA" not in page


def test_subscriptions_you_already_have_are_marked(client):
    client.post("/subscriptions/new", data=NETFLIX)
    page = upload(client, sample_bytes()).get_data(as_text=True)
    assert "Already in your list" in page


def test_confirming_adds_only_the_ticked_suggestions(client):
    form = {
        "count": "2",
        "add_0": "on", "name_0": "Netflix", "category_0": "Entertainment", "price_0": "13.49",
        "cycle_0": "monthly", "date_0": "2026-09-15",
        "name_1": "Spotify", "category_1": "Music", "price_1": "11.99",
        "cycle_1": "monthly", "date_1": "2026-09-02",
    }
    response = client.post("/subscriptions/import/confirm", data=form)
    assert "imported=1" in response.headers["Location"]
    page = client.get("/subscriptions/?imported=1").get_data(as_text=True)
    assert "subscriptions were added from your bank statement." in page
    assert "€13.49" in page
    assert "€11.99" not in page


def test_confirming_still_checks_every_value(client):
    form = {"count": "1", "add_0": "on", "name_0": "Hack", "category_0": "Cars", "price_0": "-5",
            "cycle_0": "daily", "date_0": "never"}
    response = client.post("/subscriptions/import/confirm", data=form)
    assert "imported=0" in response.headers["Location"]


def test_no_file_wrong_type_or_wrong_columns_give_an_error(client):
    response = client.post("/subscriptions/import", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert "Choose a CSV file" in response.get_data(as_text=True)

    response = upload(client, "hello", filename="statement.pdf")
    assert "must be a .csv export" in response.get_data(as_text=True)

    response = upload(client, "When,What\n2026-09-15,Netflix\n")
    assert "needs the columns Date, Description and Amount" in response.get_data(as_text=True)


def test_a_file_that_is_not_text_gives_an_error(client):
    response = upload(client, b"\xff\xfe\x00\x81\x9f binary")
    assert response.status_code == 400
    assert "could not be read" in response.get_data(as_text=True)


def test_a_statement_with_nothing_repeating(client):
    page = upload(client, "Date,Description,Amount\n2026-09-15,RENFE,-35.60\n2026-09-16,oops,abc\n")
    text = page.get_data(as_text=True)
    assert "No repeating payments found" in text
    assert "1 rows could not be read" in text


def test_files_over_1_mb_are_refused(client):
    response = upload(client, b"x" * (1024 * 1024 + 1))
    assert response.status_code == 413
