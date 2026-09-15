from anthropic import Anthropic

from trend_pipeline import config, keyword_extractor, reddit_collector, rss_collector, storage


def run() -> dict:
    cfg = config.load_config()

    try:
        reddit_client = reddit_collector.get_reddit_client(
            cfg["reddit_client_id"], cfg["reddit_client_secret"], cfg["reddit_user_agent"]
        )
        reddit_items = reddit_collector.collect_reddit_posts(reddit_client, cfg["subreddits"])
    except Exception as exc:
        print(f"Reddit 수집 실패: {exc}")
        reddit_items = []

    try:
        rss_items = rss_collector.collect_rss_entries(cfg["rss_feeds"])
    except Exception as exc:
        print(f"RSS 수집 실패: {exc}")
        rss_items = []

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
