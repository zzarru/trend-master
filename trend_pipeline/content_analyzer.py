import json

from trend_pipeline.categories import CATEGORIES, DEFAULT_CATEGORY

_PROMPT_TEMPLATE = """다음 유튜브 영상 정보를 보고, 마케팅 관점에서 아래 카테고리 중 하나로 분류하고 2~3문장으로 요약해줘.

카테고리 목록: {categories}

반드시 아래 JSON 형식으로만 응답해:
{{"category": "...", "summary": "..."}}

제목: {title}
설명: {body}
상위 댓글: {comments}
"""


def analyze_content(client, content_item: dict) -> dict:
    comments = content_item.get("top_comments") or []
    prompt = _PROMPT_TEMPLATE.format(
        categories=", ".join(CATEGORIES),
        title=content_item.get("title", ""),
        body=content_item.get("body", "")[:2000],
        comments=" / ".join(comments[:5]) if comments else "(댓글 없음)",
    )
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines)
    parsed = json.loads(stripped)

    if "category" not in parsed or "summary" not in parsed:
        raise ValueError("content analysis response missing 'category' or 'summary'")

    if parsed["category"] not in CATEGORIES:
        parsed["category"] = DEFAULT_CATEGORY

    return parsed


def analyze_content_batch(client, content_items: list[dict]) -> list[dict]:
    results = []
    for item in content_items:
        try:
            analyzed = analyze_content(client, item)
            results.append(
                {
                    "content_item": item,
                    "category": analyzed["category"],
                    "summary": analyzed["summary"],
                    "success": True,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "content_item": item,
                    "category": None,
                    "summary": None,
                    "error": str(exc),
                    "success": False,
                }
            )
    return results
