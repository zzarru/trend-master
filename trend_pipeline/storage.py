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
    collected_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER NOT NULL REFERENCES raw_content(id),
    keyword TEXT NOT NULL,
    usage_context TEXT
);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)
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


def save_keywords(conn: sqlite3.Connection, content_id: int, keywords: list[str], usage_context: str) -> None:
    conn.executemany(
        "INSERT INTO keywords (content_id, keyword, usage_context) VALUES (?, ?, ?)",
        [(content_id, keyword, usage_context) for keyword in keywords],
    )
    conn.commit()
