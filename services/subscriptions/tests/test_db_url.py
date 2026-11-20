"""How db.connect() reads DATABASE_URL (no real database needed: the driver is replaced)."""
import db


def connect_with(monkeypatch, url):
    """Call db.connect() with this DATABASE_URL and return what it passed to the driver."""
    received = {}

    def fake_connect(**options):
        received.update(options)

    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(db.pymssql, "connect", fake_connect)
    db.connect()
    return received


def test_reads_host_port_user_password_and_database(monkeypatch):
    options = connect_with(monkeypatch, "mssql://app_user:p%40ss@db.example.com:1444/shop")
    assert options["server"] == "db.example.com"
    assert options["port"] == 1444
    assert options["user"] == "app_user"
    assert options["password"] == "p@ss"      # %40 in a URL means @
    assert options["database"] == "shop"


def test_no_encryption_option_locally(monkeypatch):
    options = connect_with(monkeypatch, "mssql://app_user:secret@localhost:1433/shop")
    assert "encryption" not in options


def test_azure_url_asks_for_encryption(monkeypatch):
    url = "mssql://app_user:secret@x-sql.database.windows.net:1433/shop?encryption=require"
    options = connect_with(monkeypatch, url)
    assert options["encryption"] == "require"
    assert options["database"] == "shop"       # the ?encryption part is not in the name
