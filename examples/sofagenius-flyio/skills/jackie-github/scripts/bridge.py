#!/usr/bin/env python3
"""Standalone GitHub bridge — monitors repos for issues, PRs, and activity.

Uses urllib (stdlib) to call the GitHub REST API. No extra dependencies.
Read-only: never creates issues, comments, or modifies anything.

Execution telemetry is auto-captured to the feedback store so SofaGenius
can learn from operational patterns over time.

Usage:
    python3 bridge.py issues --repos "lilyzhng/SofaGenius" --count 10
    python3 bridge.py pulls --repos "lilyzhng/SofaGenius" --count 10
    python3 bridge.py activity --repos "lilyzhng/SofaGenius" --count 20
    python3 bridge.py summary --repos "lilyzhng/SofaGenius,openclaw/openclaw"
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
try:
    import feedback_store as _fb
except ImportError:
    _fb = None

SKILL_NAME = "jackie-github"
DEFAULT_REPOS = "lilyzhng/SofaGenius,lilyzhng/vault,lilyzhng/hand-draw"
API_BASE = "https://api.github.com"


def _gh_token():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print(json.dumps({"error": "GH_TOKEN env var is not set. Need a personal access token with repo read scope."}))
        sys.exit(1)
    return token


def _gh_get(path: str, params: dict | None = None) -> dict | list:
    """GET from GitHub REST API with auth."""
    token = _gh_token()
    url = f"{API_BASE}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        if qs:
            url = f"{url}?{qs}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _parse_repos(repos_str: str) -> list[str]:
    return [r.strip() for r in repos_str.split(",") if r.strip()]


def _log(action, args, result, success, start, error=None):
    duration = round((time.monotonic() - start) * 1000)
    if _fb:
        _fb.log_execution(SKILL_NAME, action, args, result, success, duration, error)


def issues(repos: str, count: int) -> None:
    action_args = {"repos": repos, "count": count}
    start = time.monotonic()
    try:
        all_issues = []
        for repo in _parse_repos(repos):
            raw = _gh_get(f"/repos/{repo}/issues", {
                "state": "open",
                "per_page": str(count),
                "sort": "updated",
                "direction": "desc",
            })
            for item in raw:
                # GitHub API returns PRs in /issues too — skip them
                if "pull_request" in item:
                    continue
                all_issues.append({
                    "repo": repo,
                    "number": item["number"],
                    "title": item["title"],
                    "author": item["user"]["login"] if item.get("user") else None,
                    "labels": [l["name"] for l in item.get("labels", [])],
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                    "comments": item.get("comments", 0),
                    "url": item["html_url"],
                })

        result = {"action": "issues", "count": len(all_issues), "issues": all_issues}
        print(json.dumps(result, indent=2))
        _log("issues", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        result = {"error": f"GitHub API error: {e.code} {e.reason}"}
        print(json.dumps(result, indent=2))
        _log("issues", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("issues", action_args, result, False, start, str(e))


def pulls(repos: str, count: int) -> None:
    action_args = {"repos": repos, "count": count}
    start = time.monotonic()
    try:
        all_prs = []
        for repo in _parse_repos(repos):
            raw = _gh_get(f"/repos/{repo}/pulls", {
                "state": "open",
                "per_page": str(count),
                "sort": "updated",
                "direction": "desc",
            })
            for item in raw:
                all_prs.append({
                    "repo": repo,
                    "number": item["number"],
                    "title": item["title"],
                    "author": item["user"]["login"] if item.get("user") else None,
                    "labels": [l["name"] for l in item.get("labels", [])],
                    "draft": item.get("draft", False),
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                    "mergeable": item.get("mergeable"),
                    "url": item["html_url"],
                })

        result = {"action": "pulls", "count": len(all_prs), "pull_requests": all_prs}
        print(json.dumps(result, indent=2))
        _log("pulls", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        result = {"error": f"GitHub API error: {e.code} {e.reason}"}
        print(json.dumps(result, indent=2))
        _log("pulls", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("pulls", action_args, result, False, start, str(e))


def activity(repos: str, count: int) -> None:
    action_args = {"repos": repos, "count": count}
    start = time.monotonic()
    try:
        all_events = []
        for repo in _parse_repos(repos):
            raw = _gh_get(f"/repos/{repo}/events", {"per_page": str(count)})
            for event in raw:
                all_events.append({
                    "repo": repo,
                    "type": event["type"],
                    "actor": event["actor"]["login"] if event.get("actor") else None,
                    "created_at": event["created_at"],
                    "payload_action": event.get("payload", {}).get("action"),
                })

        result = {"action": "activity", "count": len(all_events), "events": all_events}
        print(json.dumps(result, indent=2))
        _log("activity", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        result = {"error": f"GitHub API error: {e.code} {e.reason}"}
        print(json.dumps(result, indent=2))
        _log("activity", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("activity", action_args, result, False, start, str(e))


def summary(repos: str) -> None:
    action_args = {"repos": repos}
    start = time.monotonic()
    try:
        repo_summaries = []
        for repo in _parse_repos(repos):
            # Get repo info
            info = _gh_get(f"/repos/{repo}")

            # Count open issues (excluding PRs)
            raw_issues = _gh_get(f"/repos/{repo}/issues", {
                "state": "open", "per_page": "5", "sort": "updated",
            })
            open_issues = [i for i in raw_issues if "pull_request" not in i]

            # Count open PRs
            raw_prs = _gh_get(f"/repos/{repo}/pulls", {
                "state": "open", "per_page": "5", "sort": "updated",
            })

            # Latest activity
            events = _gh_get(f"/repos/{repo}/events", {"per_page": "3"})
            recent = []
            for ev in events:
                recent.append({
                    "type": ev["type"],
                    "actor": ev["actor"]["login"] if ev.get("actor") else None,
                    "created_at": ev["created_at"],
                })

            repo_summaries.append({
                "repo": repo,
                "description": info.get("description"),
                "stars": info.get("stargazers_count", 0),
                "open_issues_sample": len(open_issues),
                "open_issues_total": info.get("open_issues_count", 0),
                "open_prs_sample": len(raw_prs),
                "latest_issue": open_issues[0]["title"] if open_issues else None,
                "latest_pr": raw_prs[0]["title"] if raw_prs else None,
                "recent_activity": recent,
                "url": info["html_url"],
            })

        result = {"action": "summary", "repos": repo_summaries}
        print(json.dumps(result, indent=2))
        _log("summary", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        result = {"error": f"GitHub API error: {e.code} {e.reason}"}
        print(json.dumps(result, indent=2))
        _log("summary", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("summary", action_args, result, False, start, str(e))


def review(repo: str) -> None:
    """Deep review of a repo: README, recent commits, languages, and structure."""
    action_args = {"repo": repo}
    start = time.monotonic()
    try:
        # Repo info
        info = _gh_get(f"/repos/{repo}")

        # README content (base64-decoded)
        readme_text = ""
        try:
            import base64
            readme_raw = _gh_get(f"/repos/{repo}/readme")
            readme_text = base64.b64decode(readme_raw.get("content", "")).decode("utf-8", errors="replace")
        except urllib.error.HTTPError:
            readme_text = "(no README found)"

        # Recent commits
        commits_raw = _gh_get(f"/repos/{repo}/commits", {"per_page": "10"})
        commits = []
        for c in commits_raw:
            commits.append({
                "sha": c["sha"][:7],
                "message": c["commit"]["message"].split("\n")[0],
                "author": c["commit"]["author"]["name"] if c.get("commit", {}).get("author") else None,
                "date": c["commit"]["author"]["date"] if c.get("commit", {}).get("author") else None,
            })

        # Languages
        languages = {}
        try:
            languages = _gh_get(f"/repos/{repo}/languages")
        except urllib.error.HTTPError:
            pass

        # Top-level file tree
        tree_items = []
        try:
            tree_raw = _gh_get(f"/repos/{repo}/contents/")
            for item in tree_raw:
                tree_items.append({
                    "name": item["name"],
                    "type": item["type"],
                    "size": item.get("size", 0),
                })
        except urllib.error.HTTPError:
            pass

        result = {
            "action": "review",
            "repo": repo,
            "description": info.get("description"),
            "stars": info.get("stargazers_count", 0),
            "forks": info.get("forks_count", 0),
            "private": info.get("private", False),
            "default_branch": info.get("default_branch"),
            "created_at": info.get("created_at"),
            "updated_at": info.get("updated_at"),
            "languages": languages,
            "tree": tree_items,
            "recent_commits": commits,
            "readme": readme_text,
            "url": info["html_url"],
        }
        print(json.dumps(result, indent=2))
        _log("review", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        result = {"error": f"GitHub API error: {e.code} {e.reason}"}
        print(json.dumps(result, indent=2))
        _log("review", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("review", action_args, result, False, start, str(e))


def journal(repo: str, count: int) -> None:
    """Read recent commits with changed file contents — ideal for vault/journal tracking."""
    import base64
    action_args = {"repo": repo, "count": count}
    start = time.monotonic()
    try:
        commits_raw = _gh_get(f"/repos/{repo}/commits", {"per_page": str(count)})
        entries = []
        for c in commits_raw:
            sha = c["sha"]
            # Get full commit with file diffs
            detail = _gh_get(f"/repos/{repo}/commits/{sha}")
            files_changed = []
            for f in detail.get("files", []):
                file_entry = {
                    "filename": f["filename"],
                    "status": f["status"],
                    "additions": f.get("additions", 0),
                    "deletions": f.get("deletions", 0),
                }
                # For added/modified markdown files, fetch the content
                if f["status"] in ("added", "modified") and f["filename"].endswith(".md"):
                    try:
                        blob = _gh_get(f"/repos/{repo}/contents/{f['filename']}", {"ref": sha})
                        content = base64.b64decode(blob.get("content", "")).decode("utf-8", errors="replace")
                        # Truncate long files
                        file_entry["content"] = content[:3000]
                        if len(content) > 3000:
                            file_entry["truncated"] = True
                    except urllib.error.HTTPError:
                        pass
                # For JSON files (like goals.json), also fetch content
                elif f["status"] in ("added", "modified") and f["filename"].endswith(".json"):
                    try:
                        blob = _gh_get(f"/repos/{repo}/contents/{f['filename']}", {"ref": sha})
                        content = base64.b64decode(blob.get("content", "")).decode("utf-8", errors="replace")
                        file_entry["content"] = content[:3000]
                    except urllib.error.HTTPError:
                        pass
                files_changed.append(file_entry)

            entries.append({
                "sha": sha[:7],
                "message": detail["commit"]["message"],
                "author": detail["commit"]["author"]["name"] if detail.get("commit", {}).get("author") else None,
                "date": detail["commit"]["author"]["date"] if detail.get("commit", {}).get("author") else None,
                "files": files_changed,
            })

        result = {"action": "journal", "repo": repo, "count": len(entries), "entries": entries}
        print(json.dumps(result, indent=2))
        _log("journal", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        result = {"error": f"GitHub API error: {e.code} {e.reason}"}
        print(json.dumps(result, indent=2))
        _log("journal", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("journal", action_args, result, False, start, str(e))


def main() -> None:
    parser = argparse.ArgumentParser(description="Jackie GitHub Bridge")
    parser.add_argument("action", choices=["issues", "pulls", "activity", "summary", "review", "journal"])
    parser.add_argument("--repos", default=DEFAULT_REPOS,
                        help=f"Comma-separated owner/repo list (default: {DEFAULT_REPOS})")
    parser.add_argument("--count", type=int, default=10, help="Number of items (default 10)")
    args = parser.parse_args()

    if args.action == "issues":
        issues(args.repos, args.count)
    elif args.action == "pulls":
        pulls(args.repos, args.count)
    elif args.action == "activity":
        activity(args.repos, args.count)
    elif args.action == "summary":
        summary(args.repos)
    elif args.action == "review":
        # Review takes a single repo, use the first one from --repos
        repo = _parse_repos(args.repos)[0]
        review(repo)
    elif args.action == "journal":
        repo = _parse_repos(args.repos)[0]
        journal(repo, args.count)


if __name__ == "__main__":
    main()
