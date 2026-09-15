from collections import defaultdict
from datetime import datetime, timedelta, timezone

import praw


def get_reddit_client(client_id: str, client_secret: str, user_agent: str) -> praw.Reddit:
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def filter_surging_posts(posts: list[dict], min_score: int = 5, surge_multiplier: float = 2.0) -> list[dict]:
    by_subreddit = defaultdict(list)
    for post in posts:
        by_subreddit[post["subreddit"]].append(post)

    surging = []
    for subreddit_posts in by_subreddit.values():
        for post in subreddit_posts:
            if len(subreddit_posts) == 1:
                # Only one post, check against min_score
                if post["score"] >= min_score:
                    surging.append(post)
            else:
                # Calculate average excluding this post
                other_scores = [p["score"] for p in subreddit_posts if p is not post]
                avg_score = sum(other_scores) / len(other_scores)
                threshold = max(min_score, avg_score * surge_multiplier)
                if post["score"] >= threshold:
                    surging.append(post)

    return surging


def collect_reddit_posts(reddit_client, subreddits: list[str], lookback_hours: int = 24) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    candidates = []

    for subreddit_name in subreddits:
        for submission in reddit_client.subreddit(subreddit_name).new(limit=100):
            created_at = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
            if created_at < cutoff:
                continue
            candidates.append(
                {
                    "source": "reddit",
                    "source_id": submission.id,
                    "title": submission.title,
                    "body": submission.selftext,
                    "url": submission.url,
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "published_at": created_at.isoformat(),
                    "subreddit": subreddit_name,
                }
            )

    return filter_surging_posts(candidates)
