import os
import re
from datetime import datetime

from anthropic import Anthropic

from trend_pipeline import (
    config,
    content_analyzer,
    git_publisher,
    pages_checker,
    report_generator,
    slack_notifier,
    storage,
    youtube_collector,
)


def _list_archive_issues(archive_dir: str, today_str: str) -> list[dict]:
    """Existing archive dates plus today's, numbered by chronological order."""
    dates = set()
    if os.path.isdir(archive_dir):
        for fname in os.listdir(archive_dir):
            if fname.endswith(".html") and fname != "index.html":
                dates.add(fname[:-5])
    dates.add(today_str)
    return [{"issue_number": i, "date": d} for i, d in enumerate(sorted(dates), start=1)]


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

    for _, item in new_items:
        item["top_comments"] = youtube_collector.fetch_top_comments(cfg["youtube_api_key"], item["source_id"])

    anthropic_client = Anthropic(api_key=cfg["anthropic_api_key"])
    analysis_results = content_analyzer.analyze_content_batch(
        anthropic_client, [item for _, item in new_items]
    )

    analysis_success = 0
    analysis_failed = 0
    for (content_id, _), result in zip(new_items, analysis_results):
        if result["success"]:
            storage.save_analysis(conn, content_id, result["category"], result["summary"])
            analysis_success += 1
        else:
            analysis_failed += 1

    report_published = False
    slack_notified = False
    try:
        now = datetime.now().astimezone()
        today_str = now.strftime("%Y-%m-%d")
        archive_dir = os.path.join(os.path.dirname(cfg["report_path"]) or ".", "archive")
        os.makedirs(archive_dir, exist_ok=True)

        issues = _list_archive_issues(archive_dir, today_str)
        issue_number = next(i["issue_number"] for i in issues if i["date"] == today_str)

        report_html = report_generator.generate_report(conn, now, issue_number)
        with open(cfg["report_path"], "w", encoding="utf-8") as f:
            f.write(report_html)

        archive_report_html = report_generator.generate_report(
            conn, now, issue_number, archive_href="../", archive_label="← 최신 호로 돌아가기"
        )
        archive_path = os.path.join(archive_dir, f"{today_str}.html")
        with open(archive_path, "w", encoding="utf-8") as f:
            f.write(archive_report_html)

        archive_index_path = os.path.join(archive_dir, "index.html")
        with open(archive_index_path, "w", encoding="utf-8") as f:
            f.write(report_generator.generate_archive_index(issues))

        if cfg["report_base_url"]:
            report_published = git_publisher.publish(
                [cfg["report_path"], archive_path, archive_index_path], "chore: update trend report"
            )
            if report_published and cfg["slack_webhook_url"]:
                build_confirmed = True
                github_repository = cfg.get("github_repository", "")
                github_token = cfg.get("github_token", "")
                if github_repository and github_token:
                    commit_sha = git_publisher.get_head_sha()
                    build_confirmed = pages_checker.wait_for_build(
                        github_repository, github_token, commit_sha
                    )
                slack_notified = slack_notifier.notify(
                    cfg["slack_webhook_url"], cfg["report_base_url"], issue_number,
                    build_confirmed=build_confirmed,
                )
    except Exception as exc:
        print(f"리포트 생성/배포 실패: {exc}")

    summary = {
        "youtube_collected": len(youtube_items),
        "analysis_success": analysis_success,
        "analysis_failed": analysis_failed,
        "report_published": report_published,
        "slack_notified": slack_notified,
    }

    print(f"유튜브 수집: {summary['youtube_collected']}건")
    print(f"콘텐츠 분석: 성공 {summary['analysis_success']}건 / 실패 {summary['analysis_failed']}건")
    print(f"리포트 배포: {'성공' if report_published else '건너뜀/실패'}")
    print(f"슬랙 알림: {'성공' if slack_notified else '건너뜀/실패'}")

    return summary


if __name__ == "__main__":
    run()
