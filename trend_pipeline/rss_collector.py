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
