import subprocess


def publish(paths: list[str], commit_message: str, run=subprocess.run) -> bool:
    try:
        run(["git", "add", *paths], check=True, capture_output=True, text=True)
        run(["git", "commit", "-m", commit_message], check=True, capture_output=True, text=True)
        run(["git", "push"], check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        return False
