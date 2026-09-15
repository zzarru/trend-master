import json
from unittest.mock import MagicMock

import pytest

from trend_pipeline import content_analyzer


def _make_client_returning(text: str):
    client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    client.messages.create.return_value = response
    return client


def test_analyze_content_parses_json_response():
    payload = json.dumps({"category": "음악", "summary": "신곡 뮤직비디오, 팬덤 반응이 활발합니다."})
    client = _make_client_returning(payload)

    result = content_analyzer.analyze_content(client, {"title": "신곡 MV", "body": "some body"})

    assert result == {"category": "음악", "summary": "신곡 뮤직비디오, 팬덤 반응이 활발합니다."}
    client.messages.create.assert_called_once()


def test_analyze_content_includes_top_comments_in_prompt():
    payload = json.dumps({"category": "게임", "summary": "게임 플레이 클립입니다."})
    client = _make_client_returning(payload)

    content_analyzer.analyze_content(
        client, {"title": "게임 클립", "body": "body", "top_comments": ["ㅋㅋㅋ 미쳤다", "이거 실화냐"]}
    )

    prompt = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "ㅋㅋㅋ 미쳤다" in prompt
    assert "이거 실화냐" in prompt


def test_analyze_content_parses_json_wrapped_in_markdown_fence():
    payload = json.dumps({"category": "스포츠", "summary": "경기 하이라이트 클립입니다."})
    fenced = f"```json\n{payload}\n```"
    client = _make_client_returning(fenced)

    result = content_analyzer.analyze_content(client, {"title": "t", "body": "b"})

    assert result == {"category": "스포츠", "summary": "경기 하이라이트 클립입니다."}


def test_analyze_content_raises_on_api_error():
    client = MagicMock()
    client.messages.create.side_effect = RuntimeError("api down")

    with pytest.raises(RuntimeError, match="api down"):
        content_analyzer.analyze_content(client, {"title": "t", "body": "b"})


def test_analyze_content_raises_on_malformed_json():
    bad_payload = json.dumps({"summary": "some summary"})
    client = _make_client_returning(bad_payload)

    with pytest.raises(ValueError, match="missing 'category' or 'summary'"):
        content_analyzer.analyze_content(client, {"title": "t", "body": "b"})


def test_analyze_content_falls_back_to_etc_for_unknown_category():
    payload = json.dumps({"category": "이상한카테고리", "summary": "요약"})
    client = _make_client_returning(payload)

    result = content_analyzer.analyze_content(client, {"title": "t", "body": "b"})

    assert result["category"] == "기타"


def test_analyze_content_batch_continues_after_individual_failure():
    good_payload = json.dumps({"category": "음악", "summary": "요약1"})
    client = MagicMock()
    good_response = MagicMock()
    good_response.content = [MagicMock(text=good_payload)]
    client.messages.create.side_effect = [RuntimeError("boom"), good_response]

    items = [{"title": "fails", "body": ""}, {"title": "succeeds", "body": ""}]
    results = content_analyzer.analyze_content_batch(client, items)

    assert results[0]["success"] is False
    assert results[0]["category"] is None
    assert results[0]["error"] == "boom"
    assert results[1]["success"] is True
    assert results[1]["category"] == "음악"
    assert results[1]["summary"] == "요약1"
