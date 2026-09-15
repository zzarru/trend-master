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
