import requests

DEFAULT_POLL_INTERVAL = 60
DEFAULT_MAX_ATTEMPTS = 5


def wait_for_build(
    repo: str,
    token: str,
    commit_sha: str,
    poll_interval: int = DEFAULT_POLL_INTERVAL,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    get=requests.get,
    sleep=None,
) -> bool:
    if sleep is None:
        import time

        sleep = time.sleep

    url = f"https://api.github.com/repos/{repo}/pages/builds/latest"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    for attempt in range(max_attempts):
        try:
            response = get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception:
            data = {}

        if data.get("commit") == commit_sha:
            if data.get("status") == "built":
                return True
            if data.get("status") == "errored":
                return False

        if attempt < max_attempts - 1:
            sleep(poll_interval)

    return False
