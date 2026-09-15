import requests

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"


def collect_youtube_trending(api_key: str, region_code: str = "KR", max_results: int = 25) -> list[dict]:
    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": max_results,
        "key": api_key,
    }
    response = requests.get(YOUTUBE_API_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    items = []
    for video in data.get("items", []):
        snippet = video.get("snippet", {})
        statistics = video.get("statistics", {})
        items.append(
            {
                "source": "youtube",
                "source_id": video["id"],
                "title": snippet.get("title", ""),
                "body": snippet.get("description", ""),
                "url": f"https://www.youtube.com/watch?v={video['id']}",
                "score": int(statistics.get("viewCount", 0)),
                "num_comments": int(statistics.get("commentCount", 0)),
                "published_at": snippet.get("publishedAt", ""),
            }
        )
    return items
