import json

_PROMPT_TEMPLATE = """다음 콘텐츠에서 마케팅 트렌드 관점의 핵심 키워드 3~5개와, 이 콘텐츠가 어떻게 쓰이고 있는지 한 줄 요약을 뽑아줘.
반드시 아래 JSON 형식으로만 응답해:
{{"keywords": ["...", "..."], "usage_context": "..."}}

제목: {title}
본문: {body}
"""


def extract_keywords(client, content_item: dict) -> dict:
    prompt = _PROMPT_TEMPLATE.format(
        title=content_item.get("title", ""),
        body=content_item.get("body", "")[:2000],
    )
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text
    return json.loads(text)


def extract_keywords_batch(client, content_items: list[dict]) -> list[dict]:
    results = []
    for item in content_items:
        try:
            extracted = extract_keywords(client, item)
            results.append(
                {
                    "content_item": item,
                    "keywords": extracted["keywords"],
                    "usage_context": extracted["usage_context"],
                    "success": True,
                }
            )
        except Exception:
            results.append(
                {
                    "content_item": item,
                    "keywords": None,
                    "usage_context": None,
                    "success": False,
                }
            )
    return results
