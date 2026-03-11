#!/usr/bin/env python3
"""Standalone GitHub bridge — monitors repos for issues, PRs, and activity.

Uses urllib (stdlib) to call the GitHub REST API. No extra dependencies.
Supports read operations (issues, PRs, activity) and write operations (commit files).

Execution telemetry is auto-captured to the feedback store so SofaGenius
can learn from operational patterns over time.

Usage:
    python3 bridge.py issues --repos "lilyzhng/SofaGenius" --count 10
    python3 bridge.py pulls --repos "lilyzhng/SofaGenius" --count 10
    python3 bridge.py activity --repos "lilyzhng/SofaGenius" --count 20
    python3 bridge.py summary --repos "lilyzhng/SofaGenius,openclaw/openclaw"
    python3 bridge.py commit --repos "lilyzhng/vault" --path "jackie/note.md" --content "..." --message "Jackie: note"
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.parse
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


def _gh_put(path: str, body: dict) -> dict:
    """PUT to GitHub REST API with auth (for creating/updating file contents)."""
    token = _gh_token()
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="PUT", headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _gh_post(path: str, body: dict) -> dict:
    """POST to GitHub REST API with auth."""
    token = _gh_token()
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _gh_patch(path: str, body: dict) -> dict:
    """PATCH to GitHub REST API with auth."""
    token = _gh_token()
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="PATCH", headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
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


def search(repo: str, query: str, count: int) -> None:
    """Search for content across a repo using GitHub code search API."""
    action_args = {"repo": repo, "query": query, "count": count}
    start = time.monotonic()
    try:
        # GitHub code search: query + repo filter
        search_query = f"{query} repo:{repo}"
        url = f"{API_BASE}/search/code"
        token = _gh_token()
        qs = urllib.parse.urlencode({"q": search_query, "per_page": str(count)})
        req = urllib.request.Request(f"{url}?{qs}", headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())

        matches = []
        for item in data.get("items", []):
            file_path = item["path"]
            # Fetch the actual file content for each match
            file_content = ""
            try:
                blob = _gh_get(f"/repos/{repo}/contents/{file_path}")
                raw = base64.b64decode(blob.get("content", "")).decode("utf-8", errors="replace")
                # Return a window around the match (first 2000 chars to keep response manageable)
                file_content = raw[:2000]
                if len(raw) > 2000:
                    file_content += "\n... (truncated)"
            except urllib.error.HTTPError:
                pass

            matches.append({
                "path": file_path,
                "name": item["name"],
                "content": file_content,
                "url": item.get("html_url", ""),
            })

        result = {"action": "search", "repo": repo, "query": query, "total_count": data.get("total_count", 0), "matches": matches}
        print(json.dumps(result, indent=2))
        _log("search", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        result = {"error": f"GitHub API error: {e.code} {e.reason}"}
        print(json.dumps(result, indent=2))
        _log("search", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("search", action_args, result, False, start, str(e))


def commit(repo: str, path: str, content: str, message: str, append: bool = False) -> None:
    """Create or update a file in a repo via the GitHub Contents API."""
    action_args = {"repo": repo, "path": path, "message": message, "append": append}
    start = time.monotonic()
    try:
        # Check if file already exists (need sha for updates)
        existing_sha = None
        existing_content = ""
        try:
            existing = _gh_get(f"/repos/{repo}/contents/{path}")
            existing_sha = existing.get("sha")
            if append and existing.get("content"):
                existing_content = base64.b64decode(existing["content"]).decode()
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise

        # In append mode, add new content after existing content
        final_content = f"{existing_content}\n{content}" if append and existing_content else content

        body: dict = {
            "message": message,
            "content": base64.b64encode(final_content.encode()).decode(),
        }
        if existing_sha:
            body["sha"] = existing_sha

        resp = _gh_put(f"/repos/{repo}/contents/{path}", body)

        result = {
            "action": "commit",
            "repo": repo,
            "path": path,
            "sha": resp.get("commit", {}).get("sha", "")[:7],
            "created": existing_sha is None,
            "url": resp.get("content", {}).get("html_url", ""),
        }
        print(json.dumps(result, indent=2))
        _log("commit", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        result = {"error": f"GitHub API error: {e.code} {e.reason}"}
        print(json.dumps(result, indent=2))
        _log("commit", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("commit", action_args, result, False, start, str(e))


def read_file(repo: str, path: str) -> None:
    """Read a file's content from a repo via the GitHub Contents API."""
    action_args = {"repo": repo, "path": path}
    start = time.monotonic()
    try:
        resp = _gh_get(f"/repos/{repo}/contents/{path}")
        content = base64.b64decode(resp.get("content", "")).decode()
        result = {
            "action": "read_file",
            "repo": repo,
            "path": path,
            "content": content,
            "sha": resp.get("sha", ""),
        }
        print(json.dumps(result, indent=2))
        _log("read_file", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            result = {"action": "read_file", "repo": repo, "path": path, "content": "", "exists": False}
            print(json.dumps(result, indent=2))
            _log("read_file", action_args, result, True, start)
        else:
            result = {"error": f"GitHub API error: {e.code} {e.reason}"}
            print(json.dumps(result, indent=2))
            _log("read_file", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("read_file", action_args, result, False, start, str(e))


def issue_comment(repo: str, number: int, body: str) -> None:
    """Add a comment to an issue or PR."""
    action_args = {"repo": repo, "number": number}
    start = time.monotonic()
    try:
        resp = _gh_post(f"/repos/{repo}/issues/{number}/comments", {"body": body})
        result = {
            "action": "issue_comment",
            "repo": repo,
            "number": number,
            "comment_id": resp.get("id"),
            "url": resp.get("html_url", ""),
        }
        print(json.dumps(result, indent=2))
        _log("issue_comment", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        result = {"error": f"GitHub API error: {e.code} {e.reason}"}
        print(json.dumps(result, indent=2))
        _log("issue_comment", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("issue_comment", action_args, result, False, start, str(e))


def issue_close(repo: str, number: int) -> None:
    """Close an issue."""
    action_args = {"repo": repo, "number": number}
    start = time.monotonic()
    try:
        resp = _gh_patch(f"/repos/{repo}/issues/{number}", {"state": "closed"})
        result = {
            "action": "issue_close",
            "repo": repo,
            "number": number,
            "state": resp.get("state"),
            "url": resp.get("html_url", ""),
        }
        print(json.dumps(result, indent=2))
        _log("issue_close", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        result = {"error": f"GitHub API error: {e.code} {e.reason}"}
        print(json.dumps(result, indent=2))
        _log("issue_close", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("issue_close", action_args, result, False, start, str(e))


def pr_merge(repo: str, number: int, method: str = "squash") -> None:
    """Merge a pull request. Method: merge, squash, or rebase."""
    action_args = {"repo": repo, "number": number, "method": method}
    start = time.monotonic()
    try:
        resp = _gh_put(f"/repos/{repo}/pulls/{number}/merge", {"merge_method": method})
        result = {
            "action": "pr_merge",
            "repo": repo,
            "number": number,
            "merged": resp.get("merged", False),
            "sha": resp.get("sha", "")[:7],
            "message": resp.get("message", ""),
        }
        print(json.dumps(result, indent=2))
        _log("pr_merge", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode()
        except Exception:
            pass
        result = {"error": f"GitHub API error: {e.code} {e.reason}", "detail": error_body}
        print(json.dumps(result, indent=2))
        _log("pr_merge", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("pr_merge", action_args, result, False, start, str(e))


def pr_close(repo: str, number: int) -> None:
    """Close a pull request without merging."""
    action_args = {"repo": repo, "number": number}
    start = time.monotonic()
    try:
        resp = _gh_patch(f"/repos/{repo}/pulls/{number}", {"state": "closed"})
        result = {
            "action": "pr_close",
            "repo": repo,
            "number": number,
            "state": resp.get("state"),
            "url": resp.get("html_url", ""),
        }
        print(json.dumps(result, indent=2))
        _log("pr_close", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        result = {"error": f"GitHub API error: {e.code} {e.reason}"}
        print(json.dumps(result, indent=2))
        _log("pr_close", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("pr_close", action_args, result, False, start, str(e))


def checks(repo: str, ref: str) -> None:
    """Get CI check runs for a commit/branch/PR. Ref can be a SHA, branch name, or 'pr/N'."""
    action_args = {"repo": repo, "ref": ref}
    start = time.monotonic()
    try:
        # If ref looks like "pr/123", resolve to the PR's head SHA
        actual_ref = ref
        if ref.startswith("pr/"):
            pr_number = ref.split("/")[1]
            pr_data = _gh_get(f"/repos/{repo}/pulls/{pr_number}")
            actual_ref = pr_data["head"]["sha"]

        resp = _gh_get(f"/repos/{repo}/commits/{actual_ref}/check-runs")
        runs = []
        for run in resp.get("check_runs", []):
            runs.append({
                "name": run["name"],
                "status": run["status"],
                "conclusion": run.get("conclusion"),
                "started_at": run.get("started_at"),
                "completed_at": run.get("completed_at"),
                "url": run.get("html_url", ""),
            })

        result = {
            "action": "checks",
            "repo": repo,
            "ref": ref,
            "resolved_ref": actual_ref[:7] if len(actual_ref) > 7 else actual_ref,
            "total": resp.get("total_count", 0),
            "check_runs": runs,
        }
        print(json.dumps(result, indent=2))
        _log("checks", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        result = {"error": f"GitHub API error: {e.code} {e.reason}"}
        print(json.dumps(result, indent=2))
        _log("checks", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("checks", action_args, result, False, start, str(e))


def main() -> None:
    parser = argparse.ArgumentParser(description="Jackie GitHub Bridge")
    parser.add_argument("action", choices=[
        "issues", "pulls", "activity", "summary", "review", "journal",
        "commit", "read_file", "search",
        "issue_comment", "issue_close", "pr_merge", "pr_close", "checks",
    ])
    parser.add_argument("--repos", default=DEFAULT_REPOS,
                        help=f"Comma-separated owner/repo list (default: {DEFAULT_REPOS})")
    parser.add_argument("--count", type=int, default=10, help="Number of items (default 10)")
    parser.add_argument("--path", help="File path for commit action")
    parser.add_argument("--content", help="File content for commit/comment action")
    parser.add_argument("--message", help="Commit message for commit action")
    parser.add_argument("--append", action="store_true", help="Append to existing file instead of replacing")
    parser.add_argument("--query", help="Search query for search action")
    parser.add_argument("--number", type=int, help="Issue/PR number")
    parser.add_argument("--ref", help="Git ref (SHA, branch, or pr/N) for checks action")
    parser.add_argument("--method", default="squash", choices=["merge", "squash", "rebase"],
                        help="Merge method for pr_merge (default: squash)")
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
    elif args.action == "commit":
        repo = _parse_repos(args.repos)[0]
        if not args.path or not args.content:
            print(json.dumps({"error": "--path and --content are required for commit action"}))
            sys.exit(1)
        commit(repo, args.path, args.content, args.message or f"Update {args.path}", args.append)
    elif args.action == "read_file":
        repo = _parse_repos(args.repos)[0]
        if not args.path:
            print(json.dumps({"error": "--path is required for read_file action"}))
            sys.exit(1)
        read_file(repo, args.path)
    elif args.action == "search":
        repo = _parse_repos(args.repos)[0]
        if not args.query:
            print(json.dumps({"error": "--query is required for search action"}))
            sys.exit(1)
        search(repo, args.query, args.count)
    elif args.action == "issue_comment":
        repo = _parse_repos(args.repos)[0]
        if not args.number or not args.content:
            print(json.dumps({"error": "--number and --content are required for issue_comment"}))
            sys.exit(1)
        issue_comment(repo, args.number, args.content)
    elif args.action == "issue_close":
        repo = _parse_repos(args.repos)[0]
        if not args.number:
            print(json.dumps({"error": "--number is required for issue_close"}))
            sys.exit(1)
        issue_close(repo, args.number)
    elif args.action == "pr_merge":
        repo = _parse_repos(args.repos)[0]
        if not args.number:
            print(json.dumps({"error": "--number is required for pr_merge"}))
            sys.exit(1)
        pr_merge(repo, args.number, args.method)
    elif args.action == "pr_close":
        repo = _parse_repos(args.repos)[0]
        if not args.number:
            print(json.dumps({"error": "--number is required for pr_close"}))
            sys.exit(1)
        pr_close(repo, args.number)
    elif args.action == "checks":
        repo = _parse_repos(args.repos)[0]
        if not args.ref:
            print(json.dumps({"error": "--ref is required for checks (SHA, branch, or pr/N)"}))
            sys.exit(1)
        checks(repo, args.ref)


if __name__ == "__main__":
    main()
