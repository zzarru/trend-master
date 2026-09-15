import requests


def notify(webhook_url: str, report_url: str, issue_number: int, post=requests.post) -> bool:
    try:
        response = post(
            webhook_url,
            json={"text": f"트렌드위클리 {issue_number}호가 발행됐어요: {report_url}"},
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception:
        print("슬랙 알림 실패")
        return False
