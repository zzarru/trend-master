import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    body TEXT,
    url TEXT,
    score INTEGER,
    num_comments INTEGER,
    published_at TEXT,
    collected_at TEXT DEFAULT CURRENT_TIMESTAMP,
    category TEXT,
    summary TEXT
);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)

    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(raw_content)")}
    if "category" not in existing_columns:
        conn.execute("ALTER TABLE raw_content ADD COLUMN category TEXT")
    if "summary" not in existing_columns:
        conn.execute("ALTER TABLE raw_content ADD COLUMN summary TEXT")

    conn.commit()
    return conn


def save_content(conn: sqlite3.Connection, item: dict) -> int | None:
    try:
        cursor = conn.execute(
            """
            INSERT INTO raw_content
                (source, source_id, title, body, url, score, num_comments, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["source"],
                item["source_id"],
                item["title"],
                item["body"],
                item["url"],
                item["score"],
                item["num_comments"],
                item["published_at"],
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def save_analysis(conn: sqlite3.Connection, content_id: int, category: str, summary: str) -> None:
    conn.execute(
        "UPDATE raw_content SET category = ?, summary = ? WHERE id = ?",
        (category, summary, content_id),
    )
    conn.commit()
