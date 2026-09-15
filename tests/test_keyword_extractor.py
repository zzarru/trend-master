import json
from unittest.mock import MagicMock

import pytest

from trend_pipeline import keyword_extractor


def _make_client_returning(text: str):
    client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    client.messages.create.return_value = response
    return client


def test_extract_keywords_parses_json_response():
    payload = json.dumps({"keywords": ["ai", "marketing", "shorts"], "usage_context": "viral marketing thread"})
    client = _make_client_returning(payload)

    result = keyword_extractor.extract_keywords(client, {"title": "AI shorts trend", "body": "some body"})

    assert result == {"keywords": ["ai", "marketing", "shorts"], "usage_context": "viral marketing thread"}
    client.messages.create.assert_called_once()


def test_extract_keywords_raises_on_api_error():
    client = MagicMock()
    client.messages.create.side_effect = RuntimeError("api down")

    with pytest.raises(RuntimeError, match="api down"):
        keyword_extractor.extract_keywords(client, {"title": "t", "body": "b"})


def test_extract_keywords_batch_continues_after_individual_failure():
    good_payload = json.dumps({"keywords": ["kw1"], "usage_context": "ctx1"})
    client = MagicMock()
    good_response = MagicMock()
    good_response.content = [MagicMock(text=good_payload)]
    client.messages.create.side_effect = [RuntimeError("boom"), good_response]

    items = [{"title": "fails", "body": ""}, {"title": "succeeds", "body": ""}]
    results = keyword_extractor.extract_keywords_batch(client, items)

    assert results[0]["success"] is False
    assert results[0]["keywords"] is None
    assert results[1]["success"] is True
    assert results[1]["keywords"] == ["kw1"]
    assert results[1]["usage_context"] == "ctx1"
