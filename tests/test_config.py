from trend_pipeline import config


def test_load_config_reads_env_and_applies_defaults(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-youtube-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("YOUTUBE_REGION_CODE", raising=False)
    monkeypatch.delenv("YOUTUBE_MAX_RESULTS", raising=False)
    monkeypatch.delenv("TREND_PIPELINE_DB_PATH", raising=False)

    cfg = config.load_config()

    assert cfg["youtube_api_key"] == "test-youtube-key"
    assert cfg["anthropic_api_key"] == "test-key"
    assert cfg["region_code"] == config.DEFAULT_REGION_CODE
    assert cfg["max_results"] == config.DEFAULT_MAX_RESULTS
    assert cfg["db_path"] == "trend_pipeline.db"


def test_load_config_raises_when_required_keys_missing(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    import pytest
    with pytest.raises(ValueError, match="YOUTUBE_API_KEY"):
        config.load_config()


def test_load_config_applies_report_and_slack_defaults(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-youtube-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("TREND_PIPELINE_REPORT_PATH", raising=False)
    monkeypatch.delenv("REPORT_BASE_URL", raising=False)
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

    cfg = config.load_config()

    assert cfg["report_path"] == config.DEFAULT_REPORT_PATH
    assert cfg["report_base_url"] == ""
    assert cfg["slack_webhook_url"] == ""


def test_load_config_reads_report_and_slack_overrides(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-youtube-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("TREND_PIPELINE_REPORT_PATH", "out/report.html")
    monkeypatch.setenv("REPORT_BASE_URL", "https://user.github.io/repo/")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/x")

    cfg = config.load_config()

    assert cfg["report_path"] == "out/report.html"
    assert cfg["report_base_url"] == "https://user.github.io/repo/"
    assert cfg["slack_webhook_url"] == "https://hooks.slack.com/services/x"


def test_load_config_applies_github_defaults(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-youtube-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    cfg = config.load_config()

    assert cfg["github_token"] == ""
    assert cfg["github_repository"] == ""


def test_load_config_reads_github_overrides(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-youtube-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("GITHUB_TOKEN", "gh-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "user/repo")

    cfg = config.load_config()

    assert cfg["github_token"] == "gh-token"
    assert cfg["github_repository"] == "user/repo"
