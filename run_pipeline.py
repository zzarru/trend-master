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
