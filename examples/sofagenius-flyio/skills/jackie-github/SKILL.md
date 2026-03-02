---
name: jackie-github
description: Monitor your GitHub repos — check open issues, pull requests, and recent activity. Read-only access via the GitHub REST API.
metadata: {"openclaw": {"emoji": "🐙", "requires": {"anyBins": ["python3", "python"], "env": ["GH_TOKEN"]}}}
---

# Jackie GitHub

Check on your GitHub repos without opening a browser. See open issues, PRs, recent activity, or get a summary across all your repos.

## When to use

- User wants to check open issues or PRs on a repo
- User wants to see recent activity (commits, comments, releases)
- User wants a quick summary across multiple repos

## List open issues

```bash
python3 {baseDir}/scripts/bridge.py issues --repos "lilyzhng/SofaGenius" --count 10
```

Returns open issues with title, author, labels, and timestamps. Pass comma-separated repos.

## List open pull requests

```bash
python3 {baseDir}/scripts/bridge.py pulls --repos "lilyzhng/SofaGenius" --count 10
```

Returns open PRs with title, author, labels, review status, and merge status.

## Recent activity

```bash
python3 {baseDir}/scripts/bridge.py activity --repos "lilyzhng/SofaGenius" --count 20
```

Returns recent events (pushes, issues, PRs, comments, releases).

## Review a repo (README, commits, structure)

```bash
python3 {baseDir}/scripts/bridge.py review --repos "lilyzhng/hand-draw"
```

Deep review of a single repo: fetches README content, recent commits, language breakdown, and file tree. Use this when someone asks you to look at or review a project.

## Read vault/journal updates (commits + file contents)

```bash
python3 {baseDir}/scripts/bridge.py journal --repos "lilyzhng/vault" --count 5
```

Fetches recent commits with full file contents for markdown and JSON files. Use this to read Obsidian vault updates, Promise Land check-ins, goals, and daily journals. Shows what was added/modified with the actual text content.

## Summary across repos

```bash
python3 {baseDir}/scripts/bridge.py summary --repos "lilyzhng/SofaGenius"
```

Returns a combined overview: open issue/PR counts and latest activity per repo.
