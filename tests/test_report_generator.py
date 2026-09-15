from datetime import datetime

from trend_pipeline import report_generator, storage


def _make_item(source_id, title, url, score):
    return {
        "source": "youtube",
        "source_id": source_id,
        "title": title,
        "body": "body",
        "url": url,
        "score": score,
        "num_comments": 1,
        "published_at": "2026-09-15T00:00:00",
    }


def _insert(conn, source_id, title, url, score, collected_at, keywords):
    content_id = storage.save_content(conn, _make_item(source_id, title, url, score))
    conn.execute("UPDATE raw_content SET collected_at = ? WHERE id = ?", (collected_at, content_id))
    conn.commit()
    storage.save_keywords(conn, content_id, keywords, "ctx")
    return content_id


def test_generate_report_ranks_keywords_by_frequency_desc():
    conn = storage.init_db(":memory:")
    _insert(conn, "v1", "AI 커버 영상", "https://example.com/v1", 100, "2026-09-15 01:00:00", ["ai"])
    _insert(conn, "v2", "AI 챌린지", "https://example.com/v2", 500, "2026-09-15 02:00:00", ["ai"])
    _insert(conn, "v3", "브이로그", "https://example.com/v3", 10, "2026-09-15 03:00:00", ["vlog"])

    html = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0))

    assert html.index("ai (2건)") < html.index("vlog (1건)")


def test_generate_report_uses_highest_score_content_as_representative():
    conn = storage.init_db(":memory:")
    _insert(conn, "v1", "낮은 조회수 영상", "https://example.com/v1", 10, "2026-09-15 01:00:00", ["ai"])
    _insert(conn, "v2", "높은 조회수 영상", "https://example.com/v2", 999, "2026-09-15 02:00:00", ["ai"])

    html = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0))

    assert "높은 조회수 영상" in html
    assert "낮은 조회수 영상" not in html


def test_generate_report_excludes_content_outside_this_week():
    conn = storage.init_db(":memory:")
    _insert(conn, "v1", "지난달 영상", "https://example.com/v1", 100, "2026-08-01 00:00:00", ["old"])

    html = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0))

    assert "old" not in html
    assert "이번 주 수집된 트렌드가 없습니다." in html


def test_generate_report_shows_empty_state_when_no_data():
    conn = storage.init_db(":memory:")

    html = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0))

    assert "오늘 수집된 트렌드가 없습니다." in html
    assert "이번 주 수집된 트렌드가 없습니다." in html
