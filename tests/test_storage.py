import sqlite3

from trend_pipeline import storage


def make_item(source_id="abc123"):
    return {
        "source": "youtube",
        "source_id": source_id,
        "title": "Test Title",
        "body": "Test body",
        "url": "https://example.com/abc123",
        "score": 42,
        "num_comments": 7,
        "published_at": "2026-09-15T00:00:00",
    }


def test_save_content_inserts_new_row_and_returns_id():
    conn = storage.init_db(":memory:")
    content_id = storage.save_content(conn, make_item())

    assert content_id is not None
    row = conn.execute("SELECT title, source FROM raw_content WHERE id = ?", (content_id,)).fetchone()
    assert row == ("Test Title", "youtube")


def test_save_content_returns_none_for_duplicate_source_id():
    conn = storage.init_db(":memory:")
    first_id = storage.save_content(conn, make_item(source_id="dup-1"))
    second_id = storage.save_content(conn, make_item(source_id="dup-1"))

    assert first_id is not None
    assert second_id is None
    count = conn.execute("SELECT COUNT(*) FROM raw_content WHERE source_id = ?", ("dup-1",)).fetchone()[0]
    assert count == 1


def test_save_analysis_sets_category_and_summary():
    conn = storage.init_db(":memory:")
    content_id = storage.save_content(conn, make_item())

    storage.save_analysis(conn, content_id, "음악", "신곡 뮤직비디오에 대한 반응 요약")

    row = conn.execute(
        "SELECT category, summary FROM raw_content WHERE id = ?", (content_id,)
    ).fetchone()
    assert row == ("음악", "신곡 뮤직비디오에 대한 반응 요약")


def test_init_db_adds_category_and_summary_columns_to_existing_table(tmp_path):
    db_path = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE raw_content (
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
        """
    )
    conn.commit()
    conn.close()

    migrated = storage.init_db(db_path)

    columns = {row[1] for row in migrated.execute("PRAGMA table_info(raw_content)")}
    assert "category" in columns
    assert "summary" in columns

    # Re-running init_db on an already-migrated DB must not error.
    storage.init_db(db_path)
