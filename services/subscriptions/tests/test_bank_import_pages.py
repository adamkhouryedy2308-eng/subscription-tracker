import io
import os

from tests.test_subscriptions_pages import NETFLIX

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "sample_data", "bank_statement_example.csv")


def upload(client, content, filename="statement.csv"):
    """Send a file to the import endpoint like a browser does."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return client.post("/subscriptions/import", data={"statement": (io.BytesIO(content), filename)},
                       content_type="multipart/form-data")


def sample_bytes():
    with open(SAMPLE, "rb") as file:
        return file.read()


def test_visitors_without_a_token_get_401(guest):
    assert upload(guest, sample_bytes()).status_code == 401


def test_uploading_the_sample_finds_six_subscriptions(client):
    data = upload(client, sample_bytes()).get_json()
    assert data["payment_count"] == 61
    names = [suggestion["name"] for suggestion in data["suggestions"]]
    assert names == ["Basic-Fit", "ChatGPT Plus", "iCloud+", "Netflix", "Padel Club Madrid", "Spotify"]


def test_subscriptions_you_already_have_are_marked(client):
    client.post("/subscriptions", json=NETFLIX)
    suggestions = upload(client, sample_bytes()).get_json()["suggestions"]
    netflix = [s for s in suggestions if s["name"] == "Netflix"][0]
    assert netflix["already_tracked"] is True


def test_confirming_adds_the_ticked_suggestions(client):
    items = [{"name": "Netflix", "category": "Entertainment", "price": "13.49",
              "billing_cycle": "monthly", "first_payment_date": "2026-09-15"}]
    response = client.post("/subscriptions/import/confirm", json={"items": items})
    assert response.get_json() == {"added": 1}
    assert client.get("/subscriptions").get_json()["subscriptions"][0]["name"] == "Netflix"


def test_confirming_still_checks_every_value(client):
    items = [{"name": "Hack", "category": "Cars", "price": "-5",
              "billing_cycle": "daily", "first_payment_date": "never"}]
    response = client.post("/subscriptions/import/confirm", json={"items": items})
    assert response.get_json() == {"added": 0}


def test_no_file_wrong_type_or_wrong_columns_give_an_error(client):
    response = client.post("/subscriptions/import", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert "Choose a CSV file" in response.get_json()["errors"][0]

    response = upload(client, "hello", filename="statement.pdf")
    assert "must be a .csv export" in response.get_json()["errors"][0]

    response = upload(client, "When,What\n2026-09-15,Netflix\n")
    assert "needs the columns Date, Description and Amount" in response.get_json()["errors"][0]


def test_a_file_that_is_not_text_gives_an_error(client):
    response = upload(client, b"\xff\xfe\x00\x81\x9f binary")
    assert response.status_code == 400
    assert "could not be read" in response.get_json()["errors"][0]


def test_a_statement_with_nothing_repeating(client):
    data = upload(client, "Date,Description,Amount\n2026-09-15,RENFE,-35.60\n2026-09-16,oops,abc\n").get_json()
    assert data["suggestions"] == []
    assert data["skipped"] == 1


def test_files_over_1_mb_are_refused(client):
    response = upload(client, b"x" * (1024 * 1024 + 1))
    assert response.status_code == 413
    assert "1 MB" in response.get_json()["errors"][0]
