import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_REGION_CODE = "KR"
DEFAULT_MAX_RESULTS = 50
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
