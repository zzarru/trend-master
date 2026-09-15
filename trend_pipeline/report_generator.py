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
    <h1>트렌드위클리</h1>
    <div class="dateline">
      <span>__DATE_RANGE__</span>
      <span class="tag">유튜브 인기 급상승 · KR</span>
    </div>
    <p class="subhead">
      이번 주 한국 유튜브 인기 급상승 영상을 마케팅 관점 7개 카테고리로 나누고,
      카테고리별 조회수 상위 5건만 추렸습니다.
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


def _render_tab(category: str, count: int, is_first: bool) -> str:
    selected = "true" if is_first else "false"
    return (
        f'    <button class="tab" role="tab" type="button" data-target="{_TAB_IDS[category]}" '
        f'aria-selected="{selected}">{html.escape(category)}<span class="n">{count}</span></button>'
    )


def _render_section(category: str, items: list[dict], is_first: bool) -> str:
    if not items:
        body = '    <p class="empty-note">이번 주 트렌드 없음</p>'
    else:
        rows = "\n".join(
            f"""      <li>
        <span class="rank">{rank:02d}</span>
        <div class="item-body">
          <a class="item-title" href="{html.escape(item['url'], quote=True)}">{html.escape(item['title'])}</a>
          <div class="item-meta">조회수 {item['score']:,}회</div>
          <p class="item-summary">{html.escape(item['summary'])}</p>
        </div>
      </li>"""
            for rank, item in enumerate(items, start=1)
        )
        body = f'    <ol class="items">\n{rows}\n    </ol>'

    hidden_attr = "" if is_first else " hidden"
    return (
        f'  <section class="category" id="{_TAB_IDS[category]}"{hidden_attr}>\n'
        f'    <div class="cat-head">\n'
        f'      <h2>{html.escape(category)}</h2>\n'
        f'      <span class="count">TOP {_TOP_N} · {len(items)}건</span>\n'
        f'    </div>\n'
        f"{body}\n"
        f"  </section>"
    )


def generate_report(conn: sqlite3.Connection, now: datetime) -> str:
    now_utc = now.astimezone(timezone.utc)
    since = (now_utc - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    range_start = now - timedelta(days=7)
    date_range = (
        f"{range_start.year}. {range_start.month}. {range_start.day} "
        f"– {now.month}. {now.day}"
    )

    data_by_category = {cat: _top_by_category(conn, since, cat) for cat in CATEGORIES}

    tabs_html = "\n".join(
        _render_tab(cat, len(data_by_category[cat]), is_first=(i == 0))
        for i, cat in enumerate(CATEGORIES)
    )
    sections_html = "\n\n".join(
        _render_section(cat, data_by_category[cat], is_first=(i == 0))
        for i, cat in enumerate(CATEGORIES)
    )

    return (
        _PAGE_TEMPLATE
        .replace("__DATE_RANGE__", html.escape(date_range))
        .replace("__TABS__", tabs_html)
        .replace("__SECTIONS__", sections_html)
        .replace("__GENERATED_AT__", html.escape(now.isoformat(timespec="seconds")))
    )
