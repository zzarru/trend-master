import html
import sqlite3
from datetime import datetime, timedelta, timezone

from trend_pipeline.categories import CATEGORIES

_TAB_IDS = {
    "엔터테인먼트": "cat-ent",
    "음악": "cat-music",
    "뷰티/패션": "cat-beauty",
    "라이프스타일": "cat-life",
    "게임": "cat-game",
    "AI/IT": "cat-ai",
    "스포츠": "cat-sports",
    "기타": "cat-etc",
}

_TOP_N = 5
_TOP_OVERALL_N = 10

_PAGE_TEMPLATE = """<title>트렌드위클리</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Nanum+Myeongjo:wght@400;700;800&family=Noto+Serif+KR:wght@400;500;600&family=Noto+Sans+KR:wght@400;500;600&display=swap">
<style>
  :root {
    --paper: #f2f0e9;
    --ink: #1d1b17;
    --ink-soft: #4a463f;
    --ink-faint: #8a8477;
    --rule: #cfc9ba;
    --rule-strong: #1d1b17;
    --accent: #8c2f27;
  }

  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --paper: #17181a;
      --ink: #eeece4;
      --ink-soft: #bcb7a9;
      --ink-faint: #726d61;
      --rule: #3a3a37;
      --rule-strong: #eeece4;
      --accent: #d9695c;
    }
  }

  :root[data-theme="dark"] {
    --paper: #17181a;
    --ink: #eeece4;
    --ink-soft: #bcb7a9;
    --ink-faint: #726d61;
    --rule: #3a3a37;
    --rule-strong: #eeece4;
    --accent: #d9695c;
  }

  * { box-sizing: border-box; }

  body {
    background: var(--paper);
    color: var(--ink);
    font-family: "Noto Serif KR", Georgia, serif;
    margin: 0;
    padding-inline: 20px;
    padding-block: 36px 64px;
  }

  .sheet { max-width: 640px; margin-inline: auto; }

  .masthead { text-align: center; padding-bottom: 18px; }

  .masthead .eyebrow {
    font-family: "Noto Sans KR", sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.16em;
    color: var(--accent);
  }

  .masthead h1 {
    font-family: "Nanum Myeongjo", "Noto Serif KR", serif;
    font-weight: 800;
    font-size: clamp(40px, 11vw, 58px);
    letter-spacing: 0.01em;
    margin: 0 0 10px;
    text-wrap: balance;
  }

  .masthead .dateline {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-family: "Noto Sans KR", sans-serif;
    font-size: 12px;
    color: var(--ink-soft);
    border-top: 1px solid var(--rule-strong);
    border-bottom: 3px solid var(--rule-strong);
    padding: 7px 2px;
  }

  .masthead .dateline .tag { color: var(--ink-faint); }

  .masthead .subhead {
    font-family: "Noto Sans KR", sans-serif;
    font-size: 12.5px;
    color: var(--ink-faint);
    margin-top: 10px;
    line-height: 1.6;
  }

  .masthead .archive-link {
    display: inline-block;
    margin-top: 6px;
    color: var(--accent);
    text-decoration: none;
    font-weight: 600;
  }

  .tabs {
    display: flex;
    gap: 2px;
    margin-top: 22px;
    border-bottom: 2px solid var(--rule-strong);
    overflow-x: auto;
    scrollbar-width: none;
  }

  .tabs::-webkit-scrollbar { display: none; }

  .tab {
    flex: 0 0 auto;
    appearance: none;
    background: none;
    border: none;
    cursor: pointer;
    font-family: "Noto Sans KR", sans-serif;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: var(--ink-faint);
    padding: 10px 13px 11px;
    position: relative;
    white-space: nowrap;
  }

  .tab .n {
    font-variant-numeric: tabular-nums;
    color: var(--ink-faint);
    font-weight: 500;
    margin-left: 3px;
  }

  .tab[aria-selected="true"] { color: var(--ink); }

  .tab[aria-selected="true"]::after {
    content: "";
    position: absolute;
    left: 8px;
    right: 8px;
    bottom: -2px;
    height: 3px;
    background: var(--accent);
  }

  .tab:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  section.category { margin-top: 30px; }
  section.category[hidden] { display: none; }

  .cat-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    border-bottom: 2px solid var(--rule-strong);
    padding-bottom: 6px;
  }

  .cat-head h2 {
    font-family: "Nanum Myeongjo", serif;
    font-weight: 700;
    font-size: 22px;
    margin: 0;
    letter-spacing: 0.02em;
  }

  .cat-head .count {
    font-family: "Noto Sans KR", sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.1em;
    color: var(--ink-faint);
    white-space: nowrap;
  }

  .empty-note {
    font-family: "Noto Serif KR", serif;
    font-style: italic;
    color: var(--ink-faint);
    font-size: 14px;
    padding: 16px 0 4px;
  }

  ol.items { list-style: none; margin: 0; padding: 0; }

  ol.items li {
    display: grid;
    grid-template-columns: 30px 1fr;
    gap: 4px 14px;
    padding: 16px 0;
    border-bottom: 1px solid var(--rule);
  }

  ol.items li:last-child { border-bottom: none; }

  .rank {
    font-family: "Nanum Myeongjo", serif;
    font-weight: 800;
    font-size: 22px;
    color: var(--accent);
    line-height: 1.15;
    font-variant-numeric: tabular-nums;
  }

  .item-body { min-width: 0; }

  .item-title {
    display: block;
    font-family: "Noto Serif KR", serif;
    font-weight: 600;
    font-size: 16.5px;
    line-height: 1.42;
    color: var(--ink);
    text-decoration: none;
  }

  .item-title:hover { color: var(--accent); }

  .item-meta {
    font-family: "Noto Sans KR", sans-serif;
    font-size: 11.5px;
    color: var(--ink-faint);
    margin-top: 4px;
    font-variant-numeric: tabular-nums;
  }

  .item-summary {
    font-family: "Noto Serif KR", serif;
    font-size: 13.5px;
    color: var(--ink-soft);
    line-height: 1.55;
    margin-top: 7px;
    max-width: 62ch;
  }

  footer {
    margin-top: 46px;
    padding-top: 14px;
    border-top: 1px solid var(--rule);
    font-family: "Noto Sans KR", sans-serif;
    font-size: 11px;
    color: var(--ink-faint);
    text-align: center;
    line-height: 1.8;
  }

  footer a { color: var(--ink-soft); }

  @media (max-width: 420px) {
    .masthead h1 { font-size: 38px; }
    .item-title { font-size: 15.5px; }
    ol.items li { grid-template-columns: 24px 1fr; }
    .rank { font-size: 18px; }
  }
</style>

<div class="sheet">
  <header class="masthead">
    <div class="eyebrow">__ISSUE_NUMBER__호</div>
    <h1>트렌드위클리</h1>
    <div class="dateline">
      <span>__DATE_RANGE__</span>
      <span class="tag">유튜브 인기 급상승 · KR</span>
    </div>
    <p class="subhead">
      이번 주 한국 유튜브 인기 급상승 영상을 탭으로 살펴보세요 —
      전체 조회수 TOP 10과, 마케팅 관점 8개 카테고리별 TOP 5.
      <a class="archive-link" href="__ARCHIVE_HREF__">__ARCHIVE_LABEL__</a>
    </p>
  </header>

  <nav class="tabs" role="tablist" aria-label="카테고리">
__TABS__
  </nav>

__SECTIONS__

  <footer>
    trend-master · run_pipeline.py 자동 발행<br>
    생성 시각: __GENERATED_AT__
  </footer>
</div>

<script>
  (function () {
    var tabs = Array.prototype.slice.call(document.querySelectorAll(".tab"));
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        var targetId = tab.getAttribute("data-target");
        tabs.forEach(function (t) {
          t.setAttribute("aria-selected", t === tab ? "true" : "false");
        });
        document.querySelectorAll("section.category").forEach(function (section) {
          section.hidden = section.id !== targetId;
        });
        tab.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" });
      });
    });
  })();
</script>
"""


def _top_by_category(conn: sqlite3.Connection, since: str, category: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT title, url, score, summary
        FROM raw_content
        WHERE collected_at >= ? AND category = ?
        ORDER BY score DESC
        LIMIT ?
        """,
        (since, category, _TOP_N),
    ).fetchall()
    return [
        {"title": title, "url": url, "score": score or 0, "summary": summary or ""}
        for title, url, score, summary in rows
    ]


def _top_overall(conn: sqlite3.Connection, since: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT title, url, score, summary, category
        FROM raw_content
        WHERE collected_at >= ?
        ORDER BY score DESC
        LIMIT ?
        """,
        (since, _TOP_OVERALL_N),
    ).fetchall()
    return [
        {"title": title, "url": url, "score": score or 0, "summary": summary or "", "category": category or ""}
        for title, url, score, summary, category in rows
    ]


def _render_tab(label: str, target_id: str, count: int, is_first: bool) -> str:
    selected = "true" if is_first else "false"
    return (
        f'    <button class="tab" role="tab" type="button" data-target="{target_id}" '
        f'aria-selected="{selected}">{html.escape(label)}<span class="n">{count}</span></button>'
    )


def _render_items_section(
    label: str, target_id: str, items: list[dict], is_first: bool, top_n: int, show_category_tag: bool = False
) -> str:
    if not items:
        body = '    <p class="empty-note">이번 주 트렌드 없음</p>'
    else:
        rows = "\n".join(
            f"""      <li>
        <span class="rank">{rank:02d}</span>
        <div class="item-body">
          <a class="item-title" href="{html.escape(item['url'], quote=True)}">{html.escape(item['title'])}</a>
          <div class="item-meta">조회수 {item['score']:,}회{
              f" · {html.escape(item['category'])}" if show_category_tag else ""
          }</div>
          <p class="item-summary">{html.escape(item['summary'])}</p>
        </div>
      </li>"""
            for rank, item in enumerate(items, start=1)
        )
        body = f'    <ol class="items">\n{rows}\n    </ol>'

    hidden_attr = "" if is_first else " hidden"
    return (
        f'  <section class="category" id="{target_id}"{hidden_attr}>\n'
        f'    <div class="cat-head">\n'
        f'      <h2>{html.escape(label)}</h2>\n'
        f'      <span class="count">TOP {top_n} · {len(items)}건</span>\n'
        f'    </div>\n'
        f"{body}\n"
        f"  </section>"
    )


def generate_report(
    conn: sqlite3.Connection,
    now: datetime,
    issue_number: int,
    archive_href: str = "archive/",
    archive_label: str = "지난 호 보기 →",
) -> str:
    now_utc = now.astimezone(timezone.utc)
    since = (now_utc - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    range_start = now - timedelta(days=7)
    date_range = (
        f"{range_start.year}. {range_start.month}. {range_start.day} "
        f"– {now.month}. {now.day}"
    )

    overall_items = _top_overall(conn, since)
    data_by_category = {cat: _top_by_category(conn, since, cat) for cat in CATEGORIES}

    tabs_html = "\n".join(
        [_render_tab("전체", "top-overall", len(overall_items), is_first=True)]
        + [_render_tab(cat, _TAB_IDS[cat], len(data_by_category[cat]), is_first=False) for cat in CATEGORIES]
    )
    sections_html = "\n\n".join(
        [_render_items_section("전체 TOP 10", "top-overall", overall_items, is_first=True, top_n=_TOP_OVERALL_N, show_category_tag=True)]
        + [
            _render_items_section(cat, _TAB_IDS[cat], data_by_category[cat], is_first=False, top_n=_TOP_N)
            for cat in CATEGORIES
        ]
    )

    return (
        _PAGE_TEMPLATE
        .replace("__ISSUE_NUMBER__", str(issue_number))
        .replace("__ARCHIVE_HREF__", html.escape(archive_href, quote=True))
        .replace("__ARCHIVE_LABEL__", html.escape(archive_label))
        .replace("__DATE_RANGE__", html.escape(date_range))
        .replace("__TABS__", tabs_html)
        .replace("__SECTIONS__", sections_html)
        .replace("__GENERATED_AT__", html.escape(now.isoformat(timespec="seconds")))
    )


_ARCHIVE_INDEX_TEMPLATE = """<title>트렌드위클리 아카이브</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Nanum+Myeongjo:wght@400;700;800&family=Noto+Serif+KR:wght@400;500;600&family=Noto+Sans+KR:wght@400;500;600&display=swap">
<style>
  :root {
    --paper: #f2f0e9;
    --ink: #1d1b17;
    --ink-soft: #4a463f;
    --ink-faint: #8a8477;
    --rule: #cfc9ba;
    --rule-strong: #1d1b17;
    --accent: #8c2f27;
  }

  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --paper: #17181a;
      --ink: #eeece4;
      --ink-soft: #bcb7a9;
      --ink-faint: #726d61;
      --rule: #3a3a37;
      --rule-strong: #eeece4;
      --accent: #d9695c;
    }
  }

  :root[data-theme="dark"] {
    --paper: #17181a;
    --ink: #eeece4;
    --ink-soft: #bcb7a9;
    --ink-faint: #726d61;
    --rule: #3a3a37;
    --rule-strong: #eeece4;
    --accent: #d9695c;
  }

  * { box-sizing: border-box; }

  body {
    background: var(--paper);
    color: var(--ink);
    font-family: "Noto Serif KR", Georgia, serif;
    margin: 0;
    padding-inline: 20px;
    padding-block: 36px 64px;
  }

  .sheet { max-width: 640px; margin-inline: auto; }

  h1 {
    font-family: "Nanum Myeongjo", "Noto Serif KR", serif;
    font-weight: 800;
    font-size: clamp(30px, 8vw, 40px);
    border-bottom: 3px solid var(--rule-strong);
    padding-bottom: 14px;
    margin: 0 0 20px;
  }

  a.back-link {
    display: inline-block;
    margin-bottom: 18px;
    color: var(--ink-faint);
    font-family: "Noto Sans KR", sans-serif;
    font-size: 12.5px;
    text-decoration: none;
  }

  ol.issues { list-style: none; margin: 0; padding: 0; }

  ol.issues li {
    display: flex;
    align-items: baseline;
    gap: 12px;
    padding: 14px 0;
    border-bottom: 1px solid var(--rule);
  }

  .issue-no {
    font-family: "Nanum Myeongjo", serif;
    font-weight: 800;
    font-size: 18px;
    color: var(--accent);
    white-space: nowrap;
  }

  .issue-link {
    font-family: "Noto Serif KR", serif;
    font-weight: 600;
    color: var(--ink);
    text-decoration: none;
  }

  .empty-note {
    font-family: "Noto Serif KR", serif;
    font-style: italic;
    color: var(--ink-faint);
    font-size: 14px;
  }
</style>

<div class="sheet">
  <a class="back-link" href="../">← 최신 리포트로 돌아가기</a>
  <h1>트렌드위클리 아카이브</h1>
__ISSUES__
</div>
"""


def generate_archive_index(issues: list[dict]) -> str:
    """issues: list of {"issue_number": int, "date": "YYYY-MM-DD"}, any order."""
    ordered = sorted(issues, key=lambda i: i["issue_number"], reverse=True)

    if not ordered:
        body = '  <p class="empty-note">발행된 리포트가 없습니다.</p>'
    else:
        rows = "\n".join(
            f"""    <li>
      <span class="issue-no">{issue['issue_number']}호</span>
      <a class="issue-link" href="{html.escape(issue['date'])}.html">{html.escape(issue['date'])}</a>
    </li>"""
            for issue in ordered
        )
        body = f'  <ol class="issues">\n{rows}\n  </ol>'

    return _ARCHIVE_INDEX_TEMPLATE.replace("__ISSUES__", body)
