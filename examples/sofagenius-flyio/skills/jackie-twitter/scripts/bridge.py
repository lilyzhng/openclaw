#!/usr/bin/env python3
"""Standalone Twitter bridge — reads timeline, searches, and checks mentions.

Uses tweepy (already installed in the container) to call the Twitter API.
Read-only: never posts, likes, retweets, or modifies anything.

Execution telemetry is auto-captured to the feedback store so SofaGenius
can learn from operational patterns over time.

Usage:
    python3 bridge.py timeline --count 20
    python3 bridge.py search --query "machine learning" --count 10
    python3 bridge.py mentions --count 10
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
try:
    import feedback_store as _fb
except ImportError:
    _fb = None

SKILL_NAME = "jackie-twitter"


def _get_client():
    """Build a tweepy Client from env vars."""
    try:
        import tweepy
    except ImportError:
        print(json.dumps({"error": "tweepy is not installed. Run: pip install tweepy"}))
        sys.exit(1)

    bearer = os.environ.get("TWITTER_BEARER_TOKEN")
    if not bearer:
        print(json.dumps({"error": "TWITTER_BEARER_TOKEN env var is not set"}))
        sys.exit(1)

    return tweepy.Client(
        bearer_token=bearer,
        consumer_key=os.environ.get("TWITTER_API_KEY"),
        consumer_secret=os.environ.get("TWITTER_API_SECRET"),
        access_token=os.environ.get("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.environ.get("TWITTER_ACCESS_SECRET"),
        wait_on_rate_limit=True,
    )


def _format_tweet(tweet, includes=None):
    """Format a tweet object into a clean dict."""
    users = {}
    if includes and hasattr(includes, "get"):
        for u in includes.get("users", []):
            users[u.id] = u.username
    elif includes and hasattr(includes, "__getitem__"):
        for u in (includes.get("users") or []):
            users[u.id] = u.username

    result = {
        "id": str(tweet.id),
        "text": tweet.text,
        "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
        "author_id": str(tweet.author_id) if tweet.author_id else None,
        "author_username": users.get(tweet.author_id),
    }
    metrics = tweet.public_metrics
    if metrics:
        result["likes"] = metrics.get("like_count", 0)
        result["retweets"] = metrics.get("retweet_count", 0)
        result["replies"] = metrics.get("reply_count", 0)
    return result


def _log(action, args, result, success, start, error=None):
    duration = round((time.monotonic() - start) * 1000)
    if _fb:
        _fb.log_execution(SKILL_NAME, action, args, result, success, duration, error)


def timeline(count: int) -> None:
    client = _get_client()
    action_args = {"count": count}
    start = time.monotonic()
    try:
        # Get authenticated user's ID for home timeline
        me = client.get_me()
        if not me or not me.data:
            result = {"error": "Could not authenticate. Check your access token/secret."}
            print(json.dumps(result, indent=2))
            _log("timeline", action_args, result, False, start, "auth failed")
            return

        resp = client.get_home_timeline(
            max_results=min(count, 100),
            tweet_fields=["created_at", "author_id", "public_metrics"],
            expansions=["author_id"],
            user_fields=["username"],
        )
        tweets = []
        if resp and resp.data:
            includes = resp.includes if hasattr(resp, "includes") else {}
            tweets = [_format_tweet(t, includes) for t in resp.data]

        result = {"action": "timeline", "count": len(tweets), "tweets": tweets}
        print(json.dumps(result, indent=2))
        _log("timeline", action_args, result, True, start)
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("timeline", action_args, result, False, start, str(e))


def search(query: str, count: int) -> None:
    client = _get_client()
    action_args = {"query": query, "count": count}
    start = time.monotonic()
    try:
        resp = client.search_recent_tweets(
            query=query,
            max_results=max(min(count, 100), 10),
            tweet_fields=["created_at", "author_id", "public_metrics"],
            expansions=["author_id"],
            user_fields=["username"],
        )
        tweets = []
        if resp and resp.data:
            includes = resp.includes if hasattr(resp, "includes") else {}
            tweets = [_format_tweet(t, includes) for t in resp.data]

        result = {"action": "search", "query": query, "count": len(tweets), "tweets": tweets}
        print(json.dumps(result, indent=2))
        _log("search", action_args, result, True, start)
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("search", action_args, result, False, start, str(e))


def mentions(count: int) -> None:
    client = _get_client()
    action_args = {"count": count}
    start = time.monotonic()
    try:
        me = client.get_me()
        if not me or not me.data:
            result = {"error": "Could not authenticate. Check your access token/secret."}
            print(json.dumps(result, indent=2))
            _log("mentions", action_args, result, False, start, "auth failed")
            return

        resp = client.get_users_mentions(
            id=me.data.id,
            max_results=max(min(count, 100), 10),
            tweet_fields=["created_at", "author_id", "public_metrics"],
            expansions=["author_id"],
            user_fields=["username"],
        )
        tweets = []
        if resp and resp.data:
            includes = resp.includes if hasattr(resp, "includes") else {}
            tweets = [_format_tweet(t, includes) for t in resp.data]

        result = {"action": "mentions", "count": len(tweets), "tweets": tweets}
        print(json.dumps(result, indent=2))
        _log("mentions", action_args, result, True, start)
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("mentions", action_args, result, False, start, str(e))


def main() -> None:
    parser = argparse.ArgumentParser(description="Jackie Twitter Bridge")
    parser.add_argument("action", choices=["timeline", "search", "mentions"])
    parser.add_argument("--query", help="Search query (required for search)")
    parser.add_argument("--count", type=int, default=20, help="Number of tweets (default 20, max 100)")
    args = parser.parse_args()

    if args.action == "timeline":
        timeline(args.count)
    elif args.action == "search":
        if not args.query:
            parser.error("--query required for search")
        search(args.query, args.count)
    elif args.action == "mentions":
        mentions(args.count)


if __name__ == "__main__":
    main()
