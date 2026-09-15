from datetime import datetime

from trend_pipeline import report_generator, storage
from trend_pipeline.categories import CATEGORIES


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


def _insert(conn, source_id, title, url, score, collected_at, category, summary="요약"):
    content_id = storage.save_content(conn, _make_item(source_id, title, url, score))
    conn.execute("UPDATE raw_content SET collected_at = ? WHERE id = ?", (collected_at, content_id))
    conn.commit()
    storage.save_analysis(conn, content_id, category, summary)
    return content_id


def test_generate_report_groups_items_by_category():
    conn = storage.init_db(":memory:")
    _insert(conn, "v1", "신곡 MV", "https://example.com/v1", 100, "2026-09-15 01:00:00", "음악")
    _insert(conn, "v2", "게임 클립", "https://example.com/v2", 50, "2026-09-15 02:00:00", "게임")

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=1)

    music_section = html_out.split('id="cat-music"')[1].split("</section>")[0]
    game_section = html_out.split('id="cat-game"')[1].split("</section>")[0]
    assert "신곡 MV" in music_section
    assert "게임 클립" not in music_section
    assert "게임 클립" in game_section
    assert "신곡 MV" not in game_section


def test_generate_report_orders_items_within_category_by_score_desc():
    conn = storage.init_db(":memory:")
    _insert(conn, "v1", "낮은 조회수 영상", "https://example.com/v1", 10, "2026-09-15 01:00:00", "음악")
    _insert(conn, "v2", "높은 조회수 영상", "https://example.com/v2", 999, "2026-09-15 02:00:00", "음악")

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=1)

    assert html_out.index("높은 조회수 영상") < html_out.index("낮은 조회수 영상")


def test_generate_report_limits_each_category_to_top_5():
    conn = storage.init_db(":memory:")
    for i in range(7):
        _insert(
            conn, f"v{i}", f"영상{i}", f"https://example.com/v{i}", 100 - i,
            "2026-09-15 01:00:00", "게임",
        )

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=1)

    game_section = html_out.split('id="cat-game"')[1].split("</section>")[0]
    assert "TOP 5 · 5건" in game_section
    assert "영상5" not in game_section
    assert "영상6" not in game_section
    assert "영상0" in game_section


def test_generate_report_excludes_content_older_than_7_days():
    conn = storage.init_db(":memory:")
    _insert(conn, "v1", "지난달 영상", "https://example.com/v1", 100, "2026-08-01 00:00:00", "음악")

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=1)

    music_section = html_out.split('id="cat-music"')[1].split("</section>")[0]
    assert "지난달 영상" not in music_section
    assert "이번 주 트렌드 없음" in music_section


def test_generate_report_uses_rolling_7_day_window_not_calendar_week():
    # now = Tuesday 2026-09-15. A calendar-week (Monday-start) boundary would be
    # 2026-09-14, excluding this item collected 6 days before `now`. The rolling
    # 7-day window must include it.
    conn = storage.init_db(":memory:")
    _insert(conn, "v1", "6일 전 영상", "https://example.com/v1", 100, "2026-09-09 13:00:00", "음악")

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=1)

    music_section = html_out.split('id="cat-music"')[1].split("</section>")[0]
    assert "6일 전 영상" in music_section


def test_generate_report_excludes_content_exactly_8_days_old():
    conn = storage.init_db(":memory:")
    _insert(conn, "v1", "8일 전 영상", "https://example.com/v1", 100, "2026-09-07 12:00:00", "음악")

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=1)

    music_section = html_out.split('id="cat-music"')[1].split("</section>")[0]
    assert "8일 전 영상" not in music_section


def test_generate_report_shows_empty_state_for_categories_with_no_data():
    conn = storage.init_db(":memory:")

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=1)

    # +1 for the overall Top 10 section's own empty state
    assert html_out.count("이번 주 트렌드 없음") == len(CATEGORIES) + 1


def test_generate_report_renders_ai_it_category_tab():
    conn = storage.init_db(":memory:")
    _insert(conn, "v1", "신형 AI 코딩 에이전트 리뷰", "https://example.com/v1", 100, "2026-09-15 01:00:00", "AI/IT")

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=1)

    ai_section = html_out.split('id="cat-ai"')[1].split("</section>")[0]
    assert "신형 AI 코딩 에이전트 리뷰" in ai_section


def test_generate_report_renders_tabs_for_all_categories_with_counts():
    conn = storage.init_db(":memory:")
    _insert(conn, "v1", "신곡 MV", "https://example.com/v1", 100, "2026-09-15 01:00:00", "음악")

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=1)

    assert 'data-target="cat-music"' in html_out
    assert 'data-target="cat-game"' in html_out
    assert 'data-target="cat-etc"' in html_out
    music_tab = html_out.split('data-target="cat-music"')[1].split("</button>")[0]
    assert "<span class=\"n\">1</span>" in music_tab


def test_generate_report_only_top_overall_section_visible_by_default():
    conn = storage.init_db(":memory:")

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=1)

    top_section_tag = html_out.split('id="top-overall"')[1].split(">")[0]
    ent_section_tag = html_out.split('id="cat-ent"')[1].split(">")[0]
    music_section_tag = html_out.split('id="cat-music"')[1].split(">")[0]
    assert "hidden" not in top_section_tag
    assert "hidden" in ent_section_tag
    assert "hidden" in music_section_tag


def test_generate_report_renders_top_overall_tab_first_and_selected():
    conn = storage.init_db(":memory:")

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=1)

    tabs_nav = html_out.split('role="tablist"')[1].split("</nav>")[0]
    assert tabs_nav.index('data-target="top-overall"') < tabs_nav.index('data-target="cat-ent"')
    top_tab = tabs_nav.split('data-target="top-overall"')[1].split("</button>")[0]
    assert 'aria-selected="true"' in top_tab


def test_generate_report_shows_overall_top10_ranked_by_score_desc():
    conn = storage.init_db(":memory:")
    _insert(conn, "v1", "낮은 조회수", "https://example.com/v1", 10, "2026-09-15 01:00:00", "음악")
    _insert(conn, "v2", "높은 조회수", "https://example.com/v2", 999, "2026-09-15 02:00:00", "게임")

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=1)

    top_section = html_out.split('id="top-overall"')[1].split("</section>")[0]
    assert "높은 조회수" in top_section
    assert "낮은 조회수" in top_section
    assert top_section.index("높은 조회수") < top_section.index("낮은 조회수")


def test_generate_report_limits_overall_top_to_10():
    conn = storage.init_db(":memory:")
    for i in range(12):
        _insert(
            conn, f"v{i}", f"영상{i}", f"https://example.com/v{i}", 100 - i,
            "2026-09-15 01:00:00", "게임",
        )

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=1)

    top_section = html_out.split('id="top-overall"')[1].split("</section>")[0]
    assert "영상9" in top_section
    assert "영상10" not in top_section
    assert "영상11" not in top_section


def test_generate_report_overall_top10_shows_category_tag_per_item():
    conn = storage.init_db(":memory:")
    _insert(conn, "v1", "게임 영상", "https://example.com/v1", 500, "2026-09-15 01:00:00", "게임")

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=1)

    top_section = html_out.split('id="top-overall"')[1].split("</section>")[0]
    assert "게임" in top_section


def test_generate_report_uses_real_utc_collected_at_default_for_this_week_section():
    # Regression test for the UTC/local timezone bug: collected_at is populated by
    # SQLite's CURRENT_TIMESTAMP (UTC), left untouched here, and `now` is a real
    # local datetime with tzinfo attached (mirrors run_pipeline.py's
    # `datetime.now().astimezone()` call).
    conn = storage.init_db(":memory:")
    content_id = storage.save_content(
        conn, _make_item("v-real-now", "실시간 영상", "https://example.com/v-real-now", 42)
    )
    storage.save_analysis(conn, content_id, "음악", "실시간 요약")

    html_out = report_generator.generate_report(conn, datetime.now().astimezone(), issue_number=1)

    music_section = html_out.split('id="cat-music"')[1].split("</section>")[0]
    assert "실시간 영상" in music_section


def test_generate_report_shows_issue_number_in_masthead():
    conn = storage.init_db(":memory:")

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=7)

    masthead = html_out.split('class="masthead"')[1].split("</header>")[0]
    assert "7호" in masthead


def test_generate_report_links_to_archive_index():
    conn = storage.init_db(":memory:")

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=1)

    masthead = html_out.split('class="masthead"')[1].split("</header>")[0]
    assert 'href="archive/"' in masthead or 'href="archive/index.html"' in masthead


def test_generate_archive_index_lists_issues_newest_first():
    issues = [
        {"issue_number": 1, "date": "2026-09-15"},
        {"issue_number": 2, "date": "2026-09-16"},
    ]

    html_out = report_generator.generate_archive_index(issues)

    assert html_out.index("2호") < html_out.index("1호")
    assert 'href="2026-09-16.html"' in html_out
    assert 'href="2026-09-15.html"' in html_out
    assert "2026-09-15" in html_out
    assert "2026-09-16" in html_out


def test_generate_archive_index_shows_empty_state_when_no_issues():
    html_out = report_generator.generate_archive_index([])

    assert "발행된 리포트가 없습니다" in html_out


def test_generate_archive_index_escapes_nothing_untrusted_but_is_well_formed():
    issues = [{"issue_number": 1, "date": "2026-09-15"}]

    html_out = report_generator.generate_archive_index(issues)

    assert "<title>" in html_out
    assert "1호" in html_out


def test_generate_report_escapes_html_in_title_and_summary():
    conn = storage.init_db(":memory:")
    _insert(
        conn, "v-xss", "<script>alert(1)</script>", "https://example.com/v-xss", 1,
        "2026-09-15 01:00:00", "음악", summary="<b>bold</b> 요약",
    )

    html_out = report_generator.generate_report(conn, datetime(2026, 9, 15, 12, 0, 0), issue_number=1)

    assert "<script>alert(1)</script>" not in html_out
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_out
    assert "<b>bold</b>" not in html_out
    assert "&lt;b&gt;bold&lt;/b&gt;" in html_out
