# MVP 트렌드 수집 파이프라인 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reddit과 RSS 피드에서 반응이 급등한 트렌드 콘텐츠를 수집하고, Claude API로 핵심 키워드를 추출해 SQLite에 저장하는 수동 실행 파이프라인을 만든다.

**Architecture:** `reddit_collector.py`, `rss_collector.py`가 각각 독립적으로 원본 콘텐츠를 수집하고, `keyword_extractor.py`가 Claude API로 키워드를 뽑고, `storage.py`가 SQLite에 저장한다. `run_pipeline.py`가 이 네 모듈을 순서대로 호출하는 단일 진입점이다. 모든 외부 API 호출부는 테스트에서 mock으로 대체 가능하도록 클라이언트 객체를 인자로 주입받는 구조로 만든다.

**Tech Stack:** Python 3.11+, praw (Reddit API), feedparser (RSS), anthropic (Claude API), sqlite3 (표준 라이브러리), pytest, python-dotenv

**Spec:** `docs/superpowers/specs/2026-09-15-mvp-trend-collection-pipeline-design.md`

## Global Constraints

- 무료 API만 사용 (Reddit 개인용 앱 등록, X·인스타그램 API는 사용하지 않음)
- 수집·저장 로직은 실제 네트워크 호출 없이 함수 단위로 테스트 가능해야 함 (외부 클라이언트는 인자로 주입, 테스트에서 mock)
- 한쪽 데이터 소스(Reddit 또는 RSS)가 실패해도 다른 쪽 수집과 전체 파이프라인은 계속 진행되어야 함
- 실행 끝에 반드시 수집/추출 결과 건수를 콘솔에 출력해야 함 (완료 주장이 실제 수치로 뒷받침되어야 함)
- 스케줄링 없음 — 수동 실행 스크립트로만 동작

---

## Task 1: 프로젝트 스캐폴딩 & 설정 로딩

**Files:**
- Create: `trend_pipeline/__init__.py` (빈 파일)
- Create: `trend_pipeline/config.py`
- Create: `requirements.txt`
- Create: `.env.example`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `trend_pipeline.config.DEFAULT_SUBREDDITS: list[str]`, `trend_pipeline.config.DEFAULT_RSS_FEEDS: list[str]`, `trend_pipeline.config.load_config() -> dict` — 반환 딕셔너리 키: `reddit_client_id`, `reddit_client_secret`, `reddit_user_agent`, `anthropic_api_key`, `subreddits: list[str]`, `rss_feeds: list[str]`, `db_path: str`

- [ ] **Step 1: requirements.txt 작성**

```text
praw>=7.7,<8
feedparser>=6.0,<7
anthropic>=0.40,<1
python-dotenv>=1.0,<2
pytest>=8.0,<9
```

- [ ] **Step 2: .env.example 작성**

```text
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=trend-pipeline-mvp/0.1 by <your-reddit-username>
ANTHROPIC_API_KEY=
```

- [ ] **Step 3: 실패하는 테스트 작성**

`tests/test_config.py`:

```python
import os
from trend_pipeline import config


def test_load_config_reads_env_and_applies_defaults(monkeypatch):
    monkeypatch.setenv("REDDIT_CLIENT_ID", "test-id")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "test-agent")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("TREND_PIPELINE_DB_PATH", raising=False)

    cfg = config.load_config()

    assert cfg["reddit_client_id"] == "test-id"
    assert cfg["reddit_client_secret"] == "test-secret"
    assert cfg["reddit_user_agent"] == "test-agent"
    assert cfg["anthropic_api_key"] == "test-key"
    assert cfg["subreddits"] == config.DEFAULT_SUBREDDITS
    assert cfg["rss_feeds"] == config.DEFAULT_RSS_FEEDS
    assert cfg["db_path"] == "trend_pipeline.db"


def test_load_config_raises_when_required_keys_missing(monkeypatch):
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    import pytest
    with pytest.raises(ValueError, match="REDDIT_CLIENT_ID"):
        config.load_config()
```

- [ ] **Step 4: 테스트 실행하여 실패 확인**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'trend_pipeline'` 또는 `AttributeError`

- [ ] **Step 5: 최소 구현 작성**

`trend_pipeline/__init__.py`: (빈 파일로 생성)

`trend_pipeline/config.py`:

```python
import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_SUBREDDITS = [
    "marketing",
    "socialmedia",
    "DigitalMarketing",
    "OutOfTheLoop",
    "trends",
]

DEFAULT_RSS_FEEDS = [
    "https://www.socialmediatoday.com/feeds/news/",
    "https://blog.hubspot.com/marketing/rss.xml",
    "https://www.thinkwithgoogle.com/feed/",
]

_REQUIRED_ENV_VARS = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "ANTHROPIC_API_KEY"]


def load_config() -> dict:
    missing = [name for name in _REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return {
        "reddit_client_id": os.environ["REDDIT_CLIENT_ID"],
        "reddit_client_secret": os.environ["REDDIT_CLIENT_SECRET"],
        "reddit_user_agent": os.environ.get("REDDIT_USER_AGENT", "trend-pipeline-mvp/0.1"),
        "anthropic_api_key": os.environ["ANTHROPIC_API_KEY"],
        "subreddits": DEFAULT_SUBREDDITS,
        "rss_feeds": DEFAULT_RSS_FEEDS,
        "db_path": os.environ.get("TREND_PIPELINE_DB_PATH", "trend_pipeline.db"),
    }
```

- [ ] **Step 6: 테스트 실행하여 통과 확인**

Run: `pytest tests/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: 커밋**

```bash
git add trend_pipeline/__init__.py trend_pipeline/config.py requirements.txt .env.example tests/test_config.py
git commit -m "feat: add config loading with Reddit/RSS/Anthropic settings"
```

---

## Task 2: SQLite 저장소

**Files:**
- Create: `trend_pipeline/storage.py`
- Test: `tests/test_storage.py`

**Interfaces:**
- Consumes: 없음 (독립 모듈)
- Produces: `trend_pipeline.storage.init_db(db_path: str) -> sqlite3.Connection`, `trend_pipeline.storage.save_content(conn, item: dict) -> int | None`, `trend_pipeline.storage.save_keywords(conn, content_id: int, keywords: list[str], usage_context: str) -> None`
  - `item` 필수 키: `source` (str, "reddit" 또는 "rss"), `source_id` (str, 소스 내 고유 ID), `title` (str), `body` (str), `url` (str), `score` (int | None), `num_comments` (int | None), `published_at` (str, ISO8601)
  - `save_content`는 동일 `source_id`가 이미 있으면 `None` 반환 (중복 삽입 방지), 새로 저장했으면 삽입된 row의 `content_id` 반환

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_storage.py`:

```python
from trend_pipeline import storage


def make_item(source_id="abc123"):
    return {
        "source": "reddit",
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
    assert row == ("Test Title", "reddit")


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
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError` 또는 `AttributeError: module 'trend_pipeline.storage' has no attribute 'init_db'`

- [ ] **Step 3: 최소 구현 작성**

`trend_pipeline/storage.py`:

```python
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
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/test_storage.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add trend_pipeline/storage.py tests/test_storage.py
git commit -m "feat: add SQLite storage for raw content and keywords"
```

---

## Task 3: Reddit 수집기

**Files:**
- Create: `trend_pipeline/reddit_collector.py`
- Test: `tests/test_reddit_collector.py`

**Interfaces:**
- Consumes: 없음 (praw 클라이언트를 인자로 주입받음)
- Produces:
  - `trend_pipeline.reddit_collector.filter_surging_posts(posts: list[dict], min_score: int = 5, surge_multiplier: float = 2.0) -> list[dict]` — 순수 함수, `posts`의 각 dict는 최소 `subreddit`, `score` 키를 가짐
  - `trend_pipeline.reddit_collector.collect_reddit_posts(reddit_client, subreddits: list[str], lookback_hours: int = 24) -> list[dict]` — 반환 dict는 storage의 `item` 형식과 동일 키(`source`, `source_id`, `title`, `body`, `url`, `score`, `num_comments`, `published_at`) + 추가 키 `subreddit`을 가짐. 내부적으로 `filter_surging_posts`를 호출해 급등한 게시물만 반환

- [ ] **Step 1: 실패하는 테스트 작성 (필터 로직)**

`tests/test_reddit_collector.py`:

```python
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from trend_pipeline import reddit_collector


def test_filter_surging_posts_keeps_only_high_relative_score():
    posts = [
        {"subreddit": "marketing", "score": 10},
        {"subreddit": "marketing", "score": 12},
        {"subreddit": "marketing", "score": 100},  # surges above 2x avg of ~40.7
    ]

    result = reddit_collector.filter_surging_posts(posts, min_score=5, surge_multiplier=2.0)

    assert result == [{"subreddit": "marketing", "score": 100}]


def test_filter_surging_posts_applies_min_score_floor():
    posts = [
        {"subreddit": "trends", "score": 1},
        {"subreddit": "trends", "score": 2},
    ]

    result = reddit_collector.filter_surging_posts(posts, min_score=5, surge_multiplier=2.0)

    assert result == []


def _make_submission(post_id, title, score, num_comments, created_utc, selftext="", url="https://x.com"):
    submission = MagicMock()
    submission.id = post_id
    submission.title = title
    submission.selftext = selftext
    submission.url = url
    submission.score = score
    submission.num_comments = num_comments
    submission.created_utc = created_utc
    return submission


def test_collect_reddit_posts_builds_items_and_filters_by_lookback():
    now = datetime.now(timezone.utc)
    recent = _make_submission("p1", "Recent surging post", 200, 50, now.timestamp())
    old = _make_submission("p2", "Old post", 500, 100, (now - timedelta(days=5)).timestamp())
    baseline = _make_submission("p3", "Baseline post", 5, 1, now.timestamp())

    mock_client = MagicMock()
    mock_client.subreddit.return_value.new.return_value = [recent, old, baseline]

    result = reddit_collector.collect_reddit_posts(mock_client, ["marketing"], lookback_hours=24)

    assert len(result) == 1
    item = result[0]
    assert item["source"] == "reddit"
    assert item["source_id"] == "p1"
    assert item["title"] == "Recent surging post"
    assert item["score"] == 200
    assert item["num_comments"] == 50
    assert item["subreddit"] == "marketing"
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/test_reddit_collector.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 구현 작성**

`trend_pipeline/reddit_collector.py`:

```python
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import praw


def get_reddit_client(client_id: str, client_secret: str, user_agent: str) -> praw.Reddit:
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def filter_surging_posts(posts: list[dict], min_score: int = 5, surge_multiplier: float = 2.0) -> list[dict]:
    by_subreddit = defaultdict(list)
    for post in posts:
        by_subreddit[post["subreddit"]].append(post)

    surging = []
    for subreddit_posts in by_subreddit.values():
        avg_score = sum(p["score"] for p in subreddit_posts) / len(subreddit_posts)
        threshold = max(min_score, avg_score * surge_multiplier)
        surging.extend(p for p in subreddit_posts if p["score"] >= threshold)

    return surging


def collect_reddit_posts(reddit_client, subreddits: list[str], lookback_hours: int = 24) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    candidates = []

    for subreddit_name in subreddits:
        for submission in reddit_client.subreddit(subreddit_name).new(limit=100):
            created_at = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
            if created_at < cutoff:
                continue
            candidates.append(
                {
                    "source": "reddit",
                    "source_id": submission.id,
                    "title": submission.title,
                    "body": submission.selftext,
                    "url": submission.url,
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "published_at": created_at.isoformat(),
                    "subreddit": subreddit_name,
                }
            )

    return filter_surging_posts(candidates)
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/test_reddit_collector.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add trend_pipeline/reddit_collector.py tests/test_reddit_collector.py
git commit -m "feat: add Reddit collector with surge-based filtering"
```

---

## Task 4: RSS 수집기

**Files:**
- Create: `trend_pipeline/rss_collector.py`
- Test: `tests/test_rss_collector.py`

**Interfaces:**
- Consumes: 없음 (feedparser를 내부에서 사용, 테스트에서는 `feedparser.parse`를 monkeypatch)
- Produces: `trend_pipeline.rss_collector.collect_rss_entries(feed_urls: list[str]) -> list[dict]` — 반환 dict는 storage `item` 형식과 동일 키(`source="rss"`, `source_id`, `title`, `body`, `url`, `score=None`, `num_comments=None`, `published_at`)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_rss_collector.py`:

```python
from types import SimpleNamespace

from trend_pipeline import rss_collector


def _make_feed(entries):
    return SimpleNamespace(entries=entries)


def test_collect_rss_entries_builds_items_from_all_feeds(monkeypatch):
    feed_a_entries = [
        SimpleNamespace(
            id="entry-1",
            title="Trend Post A",
            summary="Summary A",
            link="https://a.example.com/1",
            published="2026-09-15T00:00:00Z",
        )
    ]
    feed_b_entries = [
        SimpleNamespace(
            id="entry-2",
            title="Trend Post B",
            summary="Summary B",
            link="https://b.example.com/2",
            published="2026-09-14T00:00:00Z",
        )
    ]

    def fake_parse(url):
        if url == "https://a.example.com/rss":
            return _make_feed(feed_a_entries)
        return _make_feed(feed_b_entries)

    monkeypatch.setattr(rss_collector.feedparser, "parse", fake_parse)

    result = rss_collector.collect_rss_entries(["https://a.example.com/rss", "https://b.example.com/rss"])

    assert len(result) == 2
    first = result[0]
    assert first["source"] == "rss"
    assert first["source_id"] == "entry-1"
    assert first["title"] == "Trend Post A"
    assert first["body"] == "Summary A"
    assert first["url"] == "https://a.example.com/1"
    assert first["score"] is None
    assert first["num_comments"] is None


def test_collect_rss_entries_falls_back_to_link_when_id_missing(monkeypatch):
    entry = SimpleNamespace(title="No ID Post", summary="", link="https://c.example.com/3", published="")
    monkeypatch.setattr(rss_collector.feedparser, "parse", lambda url: _make_feed([entry]))

    result = rss_collector.collect_rss_entries(["https://c.example.com/rss"])

    assert result[0]["source_id"] == "https://c.example.com/3"
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/test_rss_collector.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 구현 작성**

`trend_pipeline/rss_collector.py`:

```python
import feedparser


def collect_rss_entries(feed_urls: list[str]) -> list[dict]:
    items = []

    for feed_url in feed_urls:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            entry_id = getattr(entry, "id", None) or entry.link
            items.append(
                {
                    "source": "rss",
                    "source_id": entry_id,
                    "title": entry.title,
                    "body": getattr(entry, "summary", ""),
                    "url": entry.link,
                    "score": None,
                    "num_comments": None,
                    "published_at": getattr(entry, "published", ""),
                }
            )

    return items
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/test_rss_collector.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add trend_pipeline/rss_collector.py tests/test_rss_collector.py
git commit -m "feat: add RSS feed collector"
```

---

## Task 5: 키워드 추출기 (Claude API)

**Files:**
- Create: `trend_pipeline/keyword_extractor.py`
- Test: `tests/test_keyword_extractor.py`

**Interfaces:**
- Consumes: 없음 (anthropic 클라이언트를 인자로 주입받음)
- Produces:
  - `trend_pipeline.keyword_extractor.extract_keywords(client, content_item: dict) -> dict` — 반환값 `{"keywords": list[str], "usage_context": str}`. `content_item`은 최소 `title`, `body` 키를 가짐. API 실패 시 예외를 그대로 전파
  - `trend_pipeline.keyword_extractor.extract_keywords_batch(client, content_items: list[dict]) -> list[dict]` — 각 원소는 `{"content_item": dict, "keywords": list[str] | None, "usage_context": str | None, "success": bool}`. 개별 항목 실패는 다른 항목 처리를 막지 않음

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_keyword_extractor.py`:

```python
import json
from unittest.mock import MagicMock

import pytest

from trend_pipeline import keyword_extractor


def _make_client_returning(text: str):
    client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    client.messages.create.return_value = response
    return client


def test_extract_keywords_parses_json_response():
    payload = json.dumps({"keywords": ["ai", "marketing", "shorts"], "usage_context": "viral marketing thread"})
    client = _make_client_returning(payload)

    result = keyword_extractor.extract_keywords(client, {"title": "AI shorts trend", "body": "some body"})

    assert result == {"keywords": ["ai", "marketing", "shorts"], "usage_context": "viral marketing thread"}
    client.messages.create.assert_called_once()


def test_extract_keywords_raises_on_api_error():
    client = MagicMock()
    client.messages.create.side_effect = RuntimeError("api down")

    with pytest.raises(RuntimeError, match="api down"):
        keyword_extractor.extract_keywords(client, {"title": "t", "body": "b"})


def test_extract_keywords_batch_continues_after_individual_failure():
    good_payload = json.dumps({"keywords": ["kw1"], "usage_context": "ctx1"})
    client = MagicMock()
    good_response = MagicMock()
    good_response.content = [MagicMock(text=good_payload)]
    client.messages.create.side_effect = [RuntimeError("boom"), good_response]

    items = [{"title": "fails", "body": ""}, {"title": "succeeds", "body": ""}]
    results = keyword_extractor.extract_keywords_batch(client, items)

    assert results[0]["success"] is False
    assert results[0]["keywords"] is None
    assert results[1]["success"] is True
    assert results[1]["keywords"] == ["kw1"]
    assert results[1]["usage_context"] == "ctx1"
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/test_keyword_extractor.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 구현 작성**

`trend_pipeline/keyword_extractor.py`:

```python
import json

_PROMPT_TEMPLATE = """다음 콘텐츠에서 마케팅 트렌드 관점의 핵심 키워드 3~5개와, 이 콘텐츠가 어떻게 쓰이고 있는지 한 줄 요약을 뽑아줘.
반드시 아래 JSON 형식으로만 응답해:
{{"keywords": ["...", "..."], "usage_context": "..."}}

제목: {title}
본문: {body}
"""


def extract_keywords(client, content_item: dict) -> dict:
    prompt = _PROMPT_TEMPLATE.format(
        title=content_item.get("title", ""),
        body=content_item.get("body", "")[:2000],
    )
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text
    return json.loads(text)


def extract_keywords_batch(client, content_items: list[dict]) -> list[dict]:
    results = []
    for item in content_items:
        try:
            extracted = extract_keywords(client, item)
            results.append(
                {
                    "content_item": item,
                    "keywords": extracted["keywords"],
                    "usage_context": extracted["usage_context"],
                    "success": True,
                }
            )
        except Exception:
            results.append(
                {
                    "content_item": item,
                    "keywords": None,
                    "usage_context": None,
                    "success": False,
                }
            )
    return results
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/test_keyword_extractor.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add trend_pipeline/keyword_extractor.py tests/test_keyword_extractor.py
git commit -m "feat: add Claude-based keyword extraction"
```

---

## Task 6: 파이프라인 진입점 & 결과 요약 출력

**Files:**
- Create: `run_pipeline.py`
- Test: `tests/test_run_pipeline.py`

**Interfaces:**
- Consumes:
  - `trend_pipeline.config.load_config() -> dict`
  - `trend_pipeline.reddit_collector.get_reddit_client(client_id, client_secret, user_agent) -> praw.Reddit`
  - `trend_pipeline.reddit_collector.collect_reddit_posts(reddit_client, subreddits, lookback_hours=24) -> list[dict]`
  - `trend_pipeline.rss_collector.collect_rss_entries(feed_urls) -> list[dict]`
  - `trend_pipeline.storage.init_db(db_path) -> sqlite3.Connection`
  - `trend_pipeline.storage.save_content(conn, item) -> int | None`
  - `trend_pipeline.storage.save_keywords(conn, content_id, keywords, usage_context) -> None`
  - `trend_pipeline.keyword_extractor.extract_keywords_batch(client, content_items) -> list[dict]`
- Produces: `run_pipeline.run(anthropic_client_factory=None, reddit_client_factory=None) -> dict` — 반환값 `{"reddit_collected": int, "rss_collected": int, "keywords_success": int, "keywords_failed": int}`. 표준 출력에 동일 내용을 사람이 읽기 쉬운 형태로 출력

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_run_pipeline.py`:

```python
from unittest.mock import MagicMock, patch

import run_pipeline


@patch("run_pipeline.keyword_extractor.extract_keywords_batch")
@patch("run_pipeline.rss_collector.collect_rss_entries")
@patch("run_pipeline.reddit_collector.collect_reddit_posts")
@patch("run_pipeline.reddit_collector.get_reddit_client")
@patch("run_pipeline.config.load_config")
def test_run_collects_saves_and_returns_summary(
    mock_load_config, mock_get_reddit_client, mock_collect_reddit, mock_collect_rss, mock_extract_batch
):
    mock_load_config.return_value = {
        "reddit_client_id": "id",
        "reddit_client_secret": "secret",
        "reddit_user_agent": "agent",
        "anthropic_api_key": "key",
        "subreddits": ["marketing"],
        "rss_feeds": ["https://example.com/rss"],
        "db_path": ":memory:",
    }
    mock_get_reddit_client.return_value = MagicMock()
    mock_collect_reddit.return_value = [
        {
            "source": "reddit",
            "source_id": "r1",
            "title": "Reddit Trend",
            "body": "body",
            "url": "https://reddit.com/r1",
            "score": 100,
            "num_comments": 10,
            "published_at": "2026-09-15T00:00:00",
        }
    ]
    mock_collect_rss.return_value = [
        {
            "source": "rss",
            "source_id": "rss1",
            "title": "RSS Trend",
            "body": "body",
            "url": "https://example.com/rss1",
            "score": None,
            "num_comments": None,
            "published_at": "2026-09-15T00:00:00",
        }
    ]
    mock_extract_batch.return_value = [
        {
            "content_item": mock_collect_reddit.return_value[0],
            "keywords": ["trend"],
            "usage_context": "ctx",
            "success": True,
        },
        {
            "content_item": mock_collect_rss.return_value[0],
            "keywords": None,
            "usage_context": None,
            "success": False,
        },
    ]

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        summary = run_pipeline.run()

    assert summary == {
        "reddit_collected": 1,
        "rss_collected": 1,
        "keywords_success": 1,
        "keywords_failed": 1,
    }
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/test_run_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'run_pipeline'`

- [ ] **Step 3: 최소 구현 작성**

`run_pipeline.py`:

```python
from anthropic import Anthropic

from trend_pipeline import config, keyword_extractor, reddit_collector, rss_collector, storage


def run() -> dict:
    cfg = config.load_config()

    reddit_client = reddit_collector.get_reddit_client(
        cfg["reddit_client_id"], cfg["reddit_client_secret"], cfg["reddit_user_agent"]
    )
    reddit_items = reddit_collector.collect_reddit_posts(reddit_client, cfg["subreddits"])
    rss_items = rss_collector.collect_rss_entries(cfg["rss_feeds"])

    conn = storage.init_db(cfg["db_path"])

    new_items = []
    for item in reddit_items + rss_items:
        content_id = storage.save_content(conn, item)
        if content_id is not None:
            new_items.append((content_id, item))

    anthropic_client = Anthropic(api_key=cfg["anthropic_api_key"])
    extraction_results = keyword_extractor.extract_keywords_batch(
        anthropic_client, [item for _, item in new_items]
    )

    keywords_success = 0
    keywords_failed = 0
    for (content_id, _), result in zip(new_items, extraction_results):
        if result["success"]:
            storage.save_keywords(conn, content_id, result["keywords"], result["usage_context"])
            keywords_success += 1
        else:
            keywords_failed += 1

    summary = {
        "reddit_collected": len(reddit_items),
        "rss_collected": len(rss_items),
        "keywords_success": keywords_success,
        "keywords_failed": keywords_failed,
    }

    print(f"Reddit 수집: {summary['reddit_collected']}건")
    print(f"RSS 수집: {summary['rss_collected']}건")
    print(f"키워드 추출: 성공 {summary['keywords_success']}건 / 실패 {summary['keywords_failed']}건")

    return summary


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/test_run_pipeline.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: 전체 테스트 스위트 실행**

Run: `pytest -v`
Expected: PASS (모든 테스트, 총 12개 이상 통과)

- [ ] **Step 6: 커밋**

```bash
git add run_pipeline.py tests/test_run_pipeline.py
git commit -m "feat: wire pipeline entrypoint with summary output"
```

---

## Task 7: 실제 자격증명으로 수동 통합 확인

**Files:**
- Modify: `.env` (git에 커밋하지 않음, `.gitignore`에 추가)
- Modify: `.gitignore` (생성 또는 수정)

**Interfaces:**
- Consumes: Task 1~6에서 만든 모든 모듈
- Produces: 없음 (검증 단계, 코드 변경 없음)

- [ ] **Step 1: .gitignore에 민감 파일 추가**

`.gitignore`:

```text
.env
*.db
__pycache__/
*.pyc
```

- [ ] **Step 2: 의존성 설치**

Run: `pip install -r requirements.txt`
Expected: 설치 성공

- [ ] **Step 3: Reddit 앱 등록 및 .env 채우기**

1. https://www.reddit.com/prefs/apps 접속 (Reddit 로그인 필요)
2. "create another app" 클릭 → type은 "script" 선택
3. 발급된 client id(앱 이름 아래 문자열)와 secret을 `.env`의 `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`에 입력
4. `REDDIT_USER_AGENT`에 `trend-pipeline-mvp/0.1 by <본인 reddit 계정명>` 형식으로 입력
5. Anthropic 콘솔에서 API 키 발급 후 `ANTHROPIC_API_KEY`에 입력

- [ ] **Step 4: 실제 파이프라인 1회 실행**

Run: `python run_pipeline.py`
Expected: 콘솔에 `Reddit 수집: N건`, `RSS 수집: M건`, `키워드 추출: 성공 K건 / 실패 F건` 형태의 요약이 출력되고, 모든 값이 실제 숫자로 채워짐 (0건이 나오면 서브레딧/피드 목록이나 API 키 설정을 재확인)

- [ ] **Step 5: DB에 데이터가 쌓였는지 확인**

Run: `python -c "import sqlite3; conn = sqlite3.connect('trend_pipeline.db'); print(conn.execute('SELECT COUNT(*) FROM raw_content').fetchone()); print(conn.execute('SELECT COUNT(*) FROM keywords').fetchone())"`
Expected: 두 카운트 모두 0보다 큰 값

- [ ] **Step 6: 커밋**

```bash
git add .gitignore
git commit -m "chore: ignore local env and db files"
```
