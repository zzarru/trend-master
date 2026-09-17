import subprocess


def publish(paths: list[str], commit_message: str, run=subprocess.run) -> bool:
    try:
        run(["git", "add", *paths], check=True, capture_output=True, text=True)
        try:
            run(
                ["git", "commit", "-m", commit_message, "--", *paths],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            stdout = (exc.stdout or "")
            if "nothing to commit" not in stdout.lower():
                raise
        run(["git", "push"], check=True, capture_output=True, text=True)
        return True
    except (subprocess.CalledProcessError, OSError):
        print("git 배포 실패: 리포트를 커밋/푸시하지 못했습니다.")
        return False


def get_head_sha(run=subprocess.run) -> str:
    result = run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True)
    return result.stdout.strip()
