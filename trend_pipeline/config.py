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
