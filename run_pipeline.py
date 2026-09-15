from anthropic import Anthropic

from trend_pipeline import config, keyword_extractor, storage, youtube_collector


def run() -> dict:
    cfg = config.load_config()

    try:
        youtube_items = youtube_collector.collect_youtube_trending(
            cfg["youtube_api_key"], region_code=cfg["region_code"], max_results=cfg["max_results"]
        )
    except Exception as exc:
        print(f"유튜브 수집 실패: {exc}")
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

    summary = {
        "youtube_collected": len(youtube_items),
        "keywords_success": keywords_success,
        "keywords_failed": keywords_failed,
    }

    print(f"유튜브 수집: {summary['youtube_collected']}건")
    print(f"키워드 추출: 성공 {summary['keywords_success']}건 / 실패 {summary['keywords_failed']}건")

    return summary


if __name__ == "__main__":
    run()
