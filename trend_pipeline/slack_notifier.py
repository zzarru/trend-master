import requests


def notify(
    webhook_url: str, report_url: str, issue_number: int, post=requests.post, build_confirmed: bool = True
) -> bool:
    text = f"트렌드위클리 {issue_number}호가 발행됐어요: {report_url}"
    if not build_confirmed:
        text += " (사이트 반영까지 몇 분 더 걸릴 수 있어요)"
    try:
        response = post(
            webhook_url,
            json={"text": text},
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception:
        print("슬랙 알림 실패")
        return False
