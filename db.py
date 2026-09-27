import os
import sqlite3

DB_FILENAME = "subtrack.db"


def get_db_path():
    """Return the path of the SQLite file, creating DATA_DIR if needed."""
    data_dir = os.environ.get("DATA_DIR", "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, DB_FILENAME)


def get_connection():
    """Open a connection where rows can be read by column name."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db(table_definitions):
    """Run each CREATE TABLE statement so the tables exist at startup."""
    conn = get_connection()
    for sql in table_definitions:
        conn.execute(sql)
    conn.commit()
    conn.close()
