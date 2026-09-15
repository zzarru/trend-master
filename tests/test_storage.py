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


def test_save_keywords_links_to_content():
    conn = storage.init_db(":memory:")
    content_id = storage.save_content(conn, make_item())

    storage.save_keywords(conn, content_id, ["ai", "marketing"], "used in a viral thread")

    rows = conn.execute(
        "SELECT keyword, usage_context FROM keywords WHERE content_id = ? ORDER BY keyword", (content_id,)
    ).fetchall()
    assert rows == [("ai", "used in a viral thread"), ("marketing", "used in a viral thread")]
