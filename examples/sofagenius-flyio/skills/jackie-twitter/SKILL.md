---
name: jackie-twitter
description: Browse your Twitter timeline, search tweets by topic, and check your mentions. Read-only — never posts or likes on your behalf.
metadata: {"openclaw": {"emoji": "🐦", "requires": {"anyBins": ["python3", "python"], "env": ["TWITTER_BEARER_TOKEN"]}}}
---

# Jackie Twitter

Browse Twitter without opening the app. Read-only access to your timeline, mentions, and topic searches.

## When to use

- User wants to catch up on their Twitter timeline
- User wants to search tweets about a specific topic
- User wants to check if anyone mentioned them

## Browse home timeline

```bash
python3 {baseDir}/scripts/bridge.py timeline --count 20
```

Returns recent tweets from accounts you follow (default 20, max 100).

## Search tweets by topic

```bash
python3 {baseDir}/scripts/bridge.py search --query "machine learning" --count 10
```

Searches recent tweets matching the query. Supports Twitter search operators.

## Check your mentions

```bash
python3 {baseDir}/scripts/bridge.py mentions --count 10
```

Returns recent tweets that mention your account.
