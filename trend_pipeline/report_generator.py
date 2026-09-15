import html
import sqlite3
from datetime import datetime, timedelta, timezone


def _aggregate_keywords(conn: sqlite3.Connection, since: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT k.keyword, c.title, c.url, c.score
        FROM keywords k
        JOIN raw_content c ON k.content_id = c.id
        WHERE c.collected_at >= ?
        """,
        (since,),
    ).fetchall()

    stats: dict[str, dict] = {}
    for keyword, title, url, score in rows:
        entry = stats.setdefault(
            keyword, {"keyword": keyword, "count": 0, "title": title, "url": url, "score": None}
        )
        entry["count"] += 1
        if entry["score"] is None or (score is not None and score > entry["score"]):
            entry["title"] = title
            entry["url"] = url
            entry["score"] = score

    return sorted(stats.values(), key=lambda e: (-e["count"], e["keyword"]))


def _render_section(title: str, entries: list[dict], empty_message: str) -> str:
    if not entries:
        return f"<h2>{title}</h2>\n<p>{empty_message}</p>\n"

    items = "\n".join(
        f'<li>{html.escape(entry["keyword"])} ({entry["count"]}건) — '
        f'<a href="{html.escape(entry["url"], quote=True)}">{html.escape(entry["title"])}</a></li>'
        for entry in entries
    )
    return f"<h2>{title}</h2>\n<ol>\n{items}\n</ol>\n"


def generate_report(conn: sqlite3.Connection, now: datetime) -> str:
    now_utc = now.astimezone(timezone.utc)
    today_start = now_utc.strftime("%Y-%m-%d 00:00:00")
    week_start = (now_utc - timedelta(days=now_utc.weekday())).strftime("%Y-%m-%d 00:00:00")

    today_keywords = _aggregate_keywords(conn, today_start)
    week_keywords = _aggregate_keywords(conn, week_start)

    body = _render_section(
        "오늘의 트렌드 키워드", today_keywords, "오늘 수집된 트렌드가 없습니다."
    ) + _render_section(
        "이번 주 트렌드 키워드", week_keywords, "이번 주 수집된 트렌드가 없습니다."
    )

    return (
        '<!DOCTYPE html>\n<html lang="ko"><head><meta charset="utf-8">'
        "<title>트렌드 리포트</title></head><body>\n"
        f"<p>생성 시각: {now.isoformat(timespec='seconds')}</p>\n"
        f"{body}</body></html>\n"
    )
