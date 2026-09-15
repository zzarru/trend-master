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
