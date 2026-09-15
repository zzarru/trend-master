import requests


def notify(webhook_url: str, report_url: str, post=requests.post) -> bool:
    try:
        response = post(
            webhook_url,
            json={"text": f"오늘의 트렌드 리포트가 준비됐어요: {report_url}"},
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception:
        return False
