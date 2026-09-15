# 웹 리포트 & 슬랙 알림 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 트렌드 수집 파이프라인 끝에 "오늘/이번 주 키워드 랭킹 HTML 리포트 생성 → GitHub Pages 자동 배포 → 슬랙 알림" 3단계를 추가한다.

**Architecture:** `report_generator.py`가 SQLite에서 오늘/이번 주 키워드를 집계해 정적 HTML 문자열을 만들고, `run_pipeline.py`가 이를 `docs/index.html`에 쓴다. `git_publisher.py`가 git add/commit/push로 GitHub Pages에 배포하고, 성공하면 `slack_notifier.py`가 Incoming Webhook으로 링크 1건을 알린다. 세 모듈 모두 외부 I/O(subprocess, requests)를 인자로 주입받아 mock 가능하게 만든다.

**Tech Stack:** Python 3.11+, sqlite3(표준 라이브러리), subprocess(표준 라이브러리), requests(기존 의존성 재사용), pytest

**Spec:** `docs/superpowers/specs/2026-09-15-web-report-slack-notify-design.md`

## Global Constraints

- 리포트/배포/슬랙 알림 중 어느 하나가 실패해도 파이프라인 전체는 끝까지 실행되어야 함 (기존 유튜브 수집 실패 처리와 동일한 원칙)
- 모든 외부 I/O(git 명령 실행, HTTP 요청)는 함수 인자로 주입 가능해야 하며, 테스트는 실제 git push나 슬랙 전송 없이 동작해야 함
- 민감정보(webhook URL 등)는 에러 로그에서 redact 처리
- `REPORT_BASE_URL`이 설정되지 않으면 배포·슬랙 알림 단계를 건너뛴다 (로컬에서 GitHub 저장소 연결 전에도 파이프라인이 깨지지 않아야 함)

---

## Task 1: report_generator — 키워드 랭킹 집계 & HTML 생성

**Files:**
- Create: `trend_pipeline/report_generator.py`
- Test: `tests/test_report_generator.py`

**Interfaces:**
- Consumes: `sqlite3.Connection` (스키마는 `trend_pipeline/storage.py`의 `raw_content`, `keywords` 테이블 — `raw_content(id, source, source_id, title, body, url, score, num_comments, published_at, collected_at)`, `keywords(id, content_id, keyword, usage_context)`)
- Produces: `trend_pipeline.report_generator.generate_report(conn: sqlite3.Connection, now: datetime) -> str` — 완성된 HTML 문자열 (파일 쓰기는 호출자 책임)

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_report_generator.py
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
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/test_report_generator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'trend_pipeline.report_generator'` (또는 `AttributeError`)

- [ ] **Step 3: 최소 구현 작성**

```python
# trend_pipeline/report_generator.py
import sqlite3
from datetime import datetime, timedelta


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
        f'<li>{entry["keyword"]} ({entry["count"]}건) — '
        f'<a href="{entry["url"]}">{entry["title"]}</a></li>'
        for entry in entries
    )
    return f"<h2>{title}</h2>\n<ol>\n{items}\n</ol>\n"


def generate_report(conn: sqlite3.Connection, now: datetime) -> str:
    today_start = now.strftime("%Y-%m-%d 00:00:00")
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d 00:00:00")

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
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/test_report_generator.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 커밋**

```bash
git add trend_pipeline/report_generator.py tests/test_report_generator.py
git commit -m "feat: add keyword ranking report generator"
```

---

## Task 2: git_publisher — 정적 리포트 자동 배포

**Files:**
- Create: `trend_pipeline/git_publisher.py`
- Test: `tests/test_git_publisher.py`

**Interfaces:**
- Consumes: 없음 (독립 모듈)
- Produces: `trend_pipeline.git_publisher.publish(paths: list[str], commit_message: str, run=subprocess.run) -> bool`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_git_publisher.py
import subprocess
from unittest.mock import MagicMock

from trend_pipeline import git_publisher


def test_publish_runs_git_add_commit_push_in_order():
    mock_run = MagicMock(return_value=MagicMock(returncode=0))

    result = git_publisher.publish(["docs/index.html"], "chore: update trend report", run=mock_run)

    assert result is True
    calls = mock_run.call_args_list
    assert calls[0].args[0] == ["git", "add", "docs/index.html"]
    assert calls[1].args[0] == ["git", "commit", "-m", "chore: update trend report"]
    assert calls[2].args[0] == ["git", "push"]


def test_publish_returns_false_when_git_command_fails():
    def failing_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    result = git_publisher.publish(["docs/index.html"], "chore: update trend report", run=failing_run)

    assert result is False
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/test_git_publisher.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'trend_pipeline.git_publisher'`

- [ ] **Step 3: 최소 구현 작성**

```python
# trend_pipeline/git_publisher.py
import subprocess


def publish(paths: list[str], commit_message: str, run=subprocess.run) -> bool:
    try:
        run(["git", "add", *paths], check=True, capture_output=True, text=True)
        run(["git", "commit", "-m", commit_message], check=True, capture_output=True, text=True)
        run(["git", "push"], check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        return False
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/test_git_publisher.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add trend_pipeline/git_publisher.py tests/test_git_publisher.py
git commit -m "feat: add git-based report publisher"
```

---

## Task 3: slack_notifier — 슬랙 웹훅 알림

**Files:**
- Create: `trend_pipeline/slack_notifier.py`
- Test: `tests/test_slack_notifier.py`

**Interfaces:**
- Consumes: 없음 (독립 모듈)
- Produces: `trend_pipeline.slack_notifier.notify(webhook_url: str, report_url: str, post=requests.post) -> bool`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_slack_notifier.py
from unittest.mock import MagicMock

from trend_pipeline import slack_notifier


def test_notify_posts_message_with_report_link():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_post = MagicMock(return_value=mock_response)

    result = slack_notifier.notify(
        "https://hooks.slack.com/services/x", "https://user.github.io/repo/", post=mock_post
    )

    assert result is True
    args, kwargs = mock_post.call_args
    assert args[0] == "https://hooks.slack.com/services/x"
    assert kwargs["json"]["text"] == "오늘의 트렌드 리포트가 준비됐어요: https://user.github.io/repo/"


def test_notify_returns_false_when_request_fails():
    def failing_post(*args, **kwargs):
        raise RuntimeError("network error")

    result = slack_notifier.notify(
        "https://hooks.slack.com/services/x", "https://user.github.io/repo/", post=failing_post
    )

    assert result is False
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/test_slack_notifier.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'trend_pipeline.slack_notifier'`

- [ ] **Step 3: 최소 구현 작성**

```python
# trend_pipeline/slack_notifier.py
import requests


def notify(webhook_url: str, report_url: str, post=requests.post) -> bool:
    try:
        response = post(
            webhook_url,
            json={"text": f"오늘의 트렌드 리포트가 준비됐어요: {report_url}"},
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception:
        return False
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/test_slack_notifier.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add trend_pipeline/slack_notifier.py tests/test_slack_notifier.py
git commit -m "feat: add Slack webhook notifier"
```

---

## Task 4: config.py — 리포트/배포/슬랙 설정 추가

**Files:**
- Modify: `trend_pipeline/config.py`
- Modify: `.env.example`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: 없음
- Produces: `load_config()`가 반환하는 dict에 `report_path`, `report_base_url`, `slack_webhook_url` 키 추가 (모두 선택값, 미설정 시 각각 기본 경로/빈 문자열)

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_config.py 에 추가
def test_load_config_applies_report_and_slack_defaults(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-youtube-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("TREND_PIPELINE_REPORT_PATH", raising=False)
    monkeypatch.delenv("REPORT_BASE_URL", raising=False)
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

    cfg = config.load_config()

    assert cfg["report_path"] == config.DEFAULT_REPORT_PATH
    assert cfg["report_base_url"] == ""
    assert cfg["slack_webhook_url"] == ""


def test_load_config_reads_report_and_slack_overrides(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-youtube-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("TREND_PIPELINE_REPORT_PATH", "out/report.html")
    monkeypatch.setenv("REPORT_BASE_URL", "https://user.github.io/repo/")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/x")

    cfg = config.load_config()

    assert cfg["report_path"] == "out/report.html"
    assert cfg["report_base_url"] == "https://user.github.io/repo/"
    assert cfg["slack_webhook_url"] == "https://hooks.slack.com/services/x"
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `KeyError: 'report_path'` (또는 `AttributeError: module 'trend_pipeline.config' has no attribute 'DEFAULT_REPORT_PATH'`)

- [ ] **Step 3: 최소 구현 작성**

```python
# trend_pipeline/config.py 전체 교체
import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_REGION_CODE = "KR"
DEFAULT_MAX_RESULTS = 25
DEFAULT_REPORT_PATH = "docs/index.html"

_REQUIRED_ENV_VARS = ["YOUTUBE_API_KEY", "ANTHROPIC_API_KEY"]


def load_config() -> dict:
    missing = [name for name in _REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return {
        "youtube_api_key": os.environ["YOUTUBE_API_KEY"],
        "anthropic_api_key": os.environ["ANTHROPIC_API_KEY"],
        "region_code": os.environ.get("YOUTUBE_REGION_CODE", DEFAULT_REGION_CODE),
        "max_results": int(os.environ.get("YOUTUBE_MAX_RESULTS", DEFAULT_MAX_RESULTS)),
        "db_path": os.environ.get("TREND_PIPELINE_DB_PATH", "trend_pipeline.db"),
        "report_path": os.environ.get("TREND_PIPELINE_REPORT_PATH", DEFAULT_REPORT_PATH),
        "report_base_url": os.environ.get("REPORT_BASE_URL", ""),
        "slack_webhook_url": os.environ.get("SLACK_WEBHOOK_URL", ""),
    }
```

```text
# .env.example 전체 교체
YOUTUBE_API_KEY=
ANTHROPIC_API_KEY=
REPORT_BASE_URL=
SLACK_WEBHOOK_URL=
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/test_config.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 커밋**

```bash
git add trend_pipeline/config.py tests/test_config.py .env.example
git commit -m "feat: add report and Slack config options"
```

---

## Task 5: run_pipeline.py — 리포트 생성·배포·알림 연결

**Files:**
- Modify: `run_pipeline.py`
- Test: `tests/test_run_pipeline.py`

**Interfaces:**
- Consumes: `report_generator.generate_report(conn, now) -> str` (Task 1), `git_publisher.publish(paths, commit_message, run=...) -> bool` (Task 2), `slack_notifier.notify(webhook_url, report_url, post=...) -> bool` (Task 3), `config.load_config()`가 반환하는 `report_path`/`report_base_url`/`slack_webhook_url` (Task 4)
- Produces: `run_pipeline.run()`이 반환하는 summary dict에 `report_published: bool`, `slack_notified: bool` 키 추가

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_run_pipeline.py 에 추가 (기존 mock_load_config.return_value들에도
# "report_path", "report_base_url", "slack_webhook_url" 키를 추가해야 KeyError가 나지 않음)

@patch("run_pipeline.slack_notifier.notify")
@patch("run_pipeline.git_publisher.publish")
@patch("run_pipeline.report_generator.generate_report")
@patch("run_pipeline.keyword_extractor.extract_keywords_batch")
@patch("run_pipeline.youtube_collector.collect_youtube_trending")
@patch("run_pipeline.config.load_config")
def test_run_publishes_report_and_notifies_slack_when_configured(
    mock_load_config, mock_collect_youtube, mock_extract_batch,
    mock_generate_report, mock_publish, mock_notify, tmp_path,
):
    report_path = tmp_path / "index.html"
    mock_load_config.return_value = {
        "youtube_api_key": "yt-key",
        "anthropic_api_key": "key",
        "region_code": "KR",
        "max_results": 25,
        "db_path": ":memory:",
        "report_path": str(report_path),
        "report_base_url": "https://user.github.io/repo/",
        "slack_webhook_url": "https://hooks.slack.com/services/x",
    }
    mock_collect_youtube.return_value = []
    mock_extract_batch.return_value = []
    mock_generate_report.return_value = "<html>report</html>"
    mock_publish.return_value = True
    mock_notify.return_value = True

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        summary = run_pipeline.run()

    assert report_path.read_text(encoding="utf-8") == "<html>report</html>"
    assert summary["report_published"] is True
    assert summary["slack_notified"] is True
    mock_publish.assert_called_once_with([str(report_path)], "chore: update trend report")
    mock_notify.assert_called_once_with("https://hooks.slack.com/services/x", "https://user.github.io/repo/")


@patch("run_pipeline.slack_notifier.notify")
@patch("run_pipeline.git_publisher.publish")
@patch("run_pipeline.report_generator.generate_report")
@patch("run_pipeline.keyword_extractor.extract_keywords_batch")
@patch("run_pipeline.youtube_collector.collect_youtube_trending")
@patch("run_pipeline.config.load_config")
def test_run_skips_publish_and_slack_when_report_base_url_missing(
    mock_load_config, mock_collect_youtube, mock_extract_batch,
    mock_generate_report, mock_publish, mock_notify, tmp_path,
):
    report_path = tmp_path / "index.html"
    mock_load_config.return_value = {
        "youtube_api_key": "yt-key",
        "anthropic_api_key": "key",
        "region_code": "KR",
        "max_results": 25,
        "db_path": ":memory:",
        "report_path": str(report_path),
        "report_base_url": "",
        "slack_webhook_url": "",
    }
    mock_collect_youtube.return_value = []
    mock_extract_batch.return_value = []
    mock_generate_report.return_value = "<html>report</html>"

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        summary = run_pipeline.run()

    assert summary["report_published"] is False
    assert summary["slack_notified"] is False
    mock_publish.assert_not_called()
    mock_notify.assert_not_called()
```

기존 3개 테스트에도 새 config 키가 없으면 `run()` 실행 중 `KeyError`가 발생하므로,
각 테스트 함수 시그니처에 `tmp_path`를 추가하고 `mock_load_config.return_value`에
`report_path`/`report_base_url`/`slack_webhook_url`을 채워 넣습니다. 세 테스트를 아래
내용으로 교체하세요 (테스트 로직 자체는 그대로, 인자와 config dict만 변경):

```python
@patch("run_pipeline.keyword_extractor.extract_keywords_batch")
@patch("run_pipeline.youtube_collector.collect_youtube_trending")
@patch("run_pipeline.config.load_config")
def test_run_collects_saves_and_returns_summary(
    mock_load_config, mock_collect_youtube, mock_extract_batch, tmp_path
):
    mock_load_config.return_value = {
        "youtube_api_key": "yt-key",
        "anthropic_api_key": "key",
        "region_code": "KR",
        "max_results": 25,
        "db_path": ":memory:",
        "report_path": str(tmp_path / "index.html"),
        "report_base_url": "",
        "slack_webhook_url": "",
    }
    mock_collect_youtube.return_value = [
        {
            "source": "youtube",
            "source_id": "v1",
            "title": "YouTube Trend",
            "body": "body",
            "url": "https://www.youtube.com/watch?v=v1",
            "score": 1000,
            "num_comments": 20,
            "published_at": "2026-09-15T00:00:00",
        }
    ]
    mock_extract_batch.return_value = [
        {
            "content_item": mock_collect_youtube.return_value[0],
            "keywords": ["trend"],
            "usage_context": "ctx",
            "success": True,
        }
    ]

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        summary = run_pipeline.run()

    assert summary["youtube_collected"] == 1
    assert summary["keywords_success"] == 1
    assert summary["keywords_failed"] == 0
    mock_collect_youtube.assert_called_once_with("yt-key", region_code="KR", max_results=25)


@patch("run_pipeline.keyword_extractor.extract_keywords_batch")
@patch("run_pipeline.youtube_collector.collect_youtube_trending")
@patch("run_pipeline.config.load_config")
def test_run_continues_when_youtube_collection_fails(
    mock_load_config, mock_collect_youtube, mock_extract_batch, tmp_path
):
    mock_load_config.return_value = {
        "youtube_api_key": "yt-key",
        "anthropic_api_key": "key",
        "region_code": "KR",
        "max_results": 25,
        "db_path": ":memory:",
        "report_path": str(tmp_path / "index.html"),
        "report_base_url": "",
        "slack_webhook_url": "",
    }
    mock_collect_youtube.side_effect = RuntimeError("quota exceeded")
    mock_extract_batch.return_value = []

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        summary = run_pipeline.run()

    assert summary["youtube_collected"] == 0
    assert summary["keywords_success"] == 0
    assert summary["keywords_failed"] == 0


@patch("run_pipeline.keyword_extractor.extract_keywords_batch")
@patch("run_pipeline.youtube_collector.collect_youtube_trending")
@patch("run_pipeline.config.load_config")
def test_run_redacts_api_key_from_failure_message(
    mock_load_config, mock_collect_youtube, mock_extract_batch, capsys, tmp_path
):
    mock_load_config.return_value = {
        "youtube_api_key": "yt-key",
        "anthropic_api_key": "key",
        "region_code": "KR",
        "max_results": 25,
        "db_path": ":memory:",
        "report_path": str(tmp_path / "index.html"),
        "report_base_url": "",
        "slack_webhook_url": "",
    }
    mock_collect_youtube.side_effect = RuntimeError(
        "403 Client Error: https://www.googleapis.com/youtube/v3/videos?"
        "part=snippet&key=SUPER_SECRET_VALUE&chart=mostPopular"
    )
    mock_extract_batch.return_value = []

    with patch("run_pipeline.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value = MagicMock()
        run_pipeline.run()

    captured = capsys.readouterr()
    assert "SUPER_SECRET_VALUE" not in captured.out
    assert "유튜브 수집 실패" in captured.out
    assert "key=***REDACTED***" in captured.out
```

(위 세 테스트는 더 이상 `summary == {...}` 형태의 딕셔너리 완전 일치로 비교하지 않고
필요한 키만 개별적으로 검증하도록 바꿨습니다 — `report_published`/`slack_notified` 키가
추가되어 완전 일치 비교가 깨지기 때문입니다.)

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/test_run_pipeline.py -v`
Expected: FAIL — 기존 테스트는 `KeyError: 'report_path'`, 새 테스트는 `AttributeError: module 'run_pipeline' has no attribute 'report_generator'`

- [ ] **Step 3: run_pipeline.py 전체 교체**

```python
# run_pipeline.py
import re
from datetime import datetime

from anthropic import Anthropic

from trend_pipeline import (
    config,
    git_publisher,
    keyword_extractor,
    report_generator,
    slack_notifier,
    storage,
    youtube_collector,
)


def run() -> dict:
    cfg = config.load_config()

    try:
        youtube_items = youtube_collector.collect_youtube_trending(
            cfg["youtube_api_key"], region_code=cfg["region_code"], max_results=cfg["max_results"]
        )
    except Exception as exc:
        sanitized = re.sub(r"key=[^&\s]+", "key=***REDACTED***", str(exc))
        print(f"유튜브 수집 실패: {sanitized}")
        youtube_items = []

    conn = storage.init_db(cfg["db_path"])

    new_items = []
    for item in youtube_items:
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

    report_html = report_generator.generate_report(conn, datetime.now())
    with open(cfg["report_path"], "w", encoding="utf-8") as f:
        f.write(report_html)

    report_published = False
    slack_notified = False
    if cfg["report_base_url"]:
        report_published = git_publisher.publish([cfg["report_path"]], "chore: update trend report")
        if report_published and cfg["slack_webhook_url"]:
            slack_notified = slack_notifier.notify(cfg["slack_webhook_url"], cfg["report_base_url"])

    summary = {
        "youtube_collected": len(youtube_items),
        "keywords_success": keywords_success,
        "keywords_failed": keywords_failed,
        "report_published": report_published,
        "slack_notified": slack_notified,
    }

    print(f"유튜브 수집: {summary['youtube_collected']}건")
    print(f"키워드 추출: 성공 {summary['keywords_success']}건 / 실패 {summary['keywords_failed']}건")
    print(f"리포트 배포: {'성공' if report_published else '건너뜀/실패'}")
    print(f"슬랙 알림: {'성공' if slack_notified else '건너뜀/실패'}")

    return summary


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/test_run_pipeline.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: 전체 테스트 스위트 실행**

Run: `pytest -q`
Expected: 모든 테스트 통과 (기존 16개 + 이번 계획에서 추가한 테스트 전부)

- [ ] **Step 6: 커밋**

```bash
git add run_pipeline.py tests/test_run_pipeline.py
git commit -m "feat: wire report generation, publishing, and Slack notification into pipeline"
```

---

## Task 6: 실제 배포 환경 연결 & 통합 검증 (사람 작업 포함)

**Files:**
- 없음 (설정/검증 작업, 코드 변경 없음)

**Interfaces:**
- Consumes: Task 1~5에서 만든 모든 모듈
- Produces: 없음 (검증 결과만 확인)

> **⚠️ 브랜치 주의사항 (최종 리뷰에서 발견):** `git_publisher.publish()`는 **현재 체크아웃된 브랜치**에 커밋하고 그 브랜치로 push합니다. 반면 GitHub Pages는 특정 브랜치(보통 `main`/`master`)만 서빙합니다. 즉, `trend-pipeline-mvp` 브랜치(이 워크트리)에서 `python run_pipeline.py`를 실행하면 리포트는 `trend-pipeline-mvp` 브랜치에 커밋되고, **Pages가 `main`을 서빙하도록 설정돼 있으면 절대 반영되지 않습니다.** 아래 Step 1에서 이 브랜치를 먼저 `main`(또는 `master`)으로 병합한 뒤, **병합된 메인 체크아웃에서** 이후 Step들을 진행하세요 (`superpowers:finishing-a-development-branch`로 병합).

- [ ] **Step 1: 브랜치 병합 & GitHub 저장소 생성/push**

이 브랜치(`trend-pipeline-mvp`)의 작업이 끝나면 `superpowers:finishing-a-development-branch`를 통해 `master`로 병합합니다. **이후 Step들은 병합된 `master` 체크아웃(워크트리가 아닌 원래 저장소 디렉터리)에서 진행하세요.**

로컬 저장소(`ai-workflow`)를 GitHub에 **public**으로 새로 만들고 push합니다 (지금은 remote가 없는 상태).

```bash
gh repo create <owner>/<repo-name> --public --source=. --remote=origin
git push -u origin master
```

- [ ] **Step 2: GitHub Pages 활성화**

GitHub 저장소 → Settings → Pages → Source를 `master` 브랜치(방금 push한, `trend-pipeline-mvp`가 병합된 브랜치)의 `/docs` 폴더로 지정합니다. (한 번만 설정하면 이후 push마다 자동 반영)

- [ ] **Step 3: 슬랙 Incoming Webhook 발급**

슬랙 워크스페이스 → https://api.slack.com/apps → "Create New App" → "Incoming Webhooks" 활성화 → 알림 받을 채널 선택 → Webhook URL 복사.

- [ ] **Step 4: .env에 추가 값 채우기**

`.env` 파일에 아래 두 줄을 추가합니다.

```text
REPORT_BASE_URL=https://<github-username>.github.io/<repo-name>/
SLACK_WEBHOOK_URL=<발급받은 webhook url>
```

- [ ] **Step 5: 파이프라인 실제 실행**

**반드시 `master` 브랜치가 체크아웃된 디렉터리에서 실행합니다** (워크트리의 `trend-pipeline-mvp` 브랜치에서 실행하면 Pages가 서빙하는 브랜치와 달라 반영되지 않습니다).

```bash
python run_pipeline.py
```

콘솔에 "리포트 배포: 성공", "슬랙 알림: 성공"이 출력되는지 확인합니다.

- [ ] **Step 6: 결과 확인**

- `docs/index.html`이 새로 생성/수정되어 `master` 브랜치에 커밋됐는지 `git log -1 --stat`으로 확인 (`git branch --show-current`로 현재 브랜치가 `master`인지도 함께 확인)
- 브라우저에서 `https://<github-username>.github.io/<repo-name>/` 접속해 리포트가 보이는지 확인 (GitHub Pages 반영까지 1~2분 소요될 수 있음)
- 슬랙 채널에 알림 메시지가 도착했는지 확인
