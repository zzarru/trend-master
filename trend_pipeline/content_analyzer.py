import json

from trend_pipeline.categories import CATEGORIES, CATEGORY_STYLE_GUIDE, DEFAULT_CATEGORY

_STYLE_GUIDE_TEXT = "\n".join(f"- {cat}: {style}" for cat, style in CATEGORY_STYLE_GUIDE.items())

_PROMPT_TEMPLATE = """다음 유튜브 영상 정보를 보고, 마케팅 관점에서 아래 카테고리 중 하나로 분류하고,
분류한 카테고리에 맞는 문체로 2~3문장 요약을 작성해줘.

카테고리 목록: {categories}

카테고리별 문체 가이드:
{style_guide}

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
        style_guide=_STYLE_GUIDE_TEXT,
        title=content_item.get("title", ""),
        body=content_item.get("body", "")[:2000],
        comments=" / ".join(comments[:5]) if comments else "(댓글 없음)",
    )
    response = client.messages.create(
        model="claude-sonnet-5",
        # Generous headroom: Claude sometimes emits a "thinking" block whose
        # tokens count against this budget, which previously left too little
        # room for the JSON output and produced truncated/unparseable JSON.
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    # Claude sometimes prepends a non-text block (e.g. extended thinking)
    # before the text block, so content[0] is not reliably the text block.
    text = None
    for block in response.content:
        candidate = getattr(block, "text", None)
        if isinstance(candidate, str):
            text = candidate
            break
    if text is None:
        raise ValueError("no text block in response")

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
