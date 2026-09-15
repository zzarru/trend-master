import requests

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_COMMENTS_API_URL = "https://www.googleapis.com/youtube/v3/commentThreads"


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


def fetch_top_comments(api_key: str, video_id: str, max_results: int = 5) -> list[str]:
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": max_results,
        "order": "relevance",
        "textFormat": "plainText",
        "key": api_key,
    }
    try:
        response = requests.get(YOUTUBE_COMMENTS_API_URL, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return []

    data = response.json()
    comments = []
    for item in data.get("items", []):
        try:
            text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
        except KeyError:
            continue
        comments.append(text)
    return comments
