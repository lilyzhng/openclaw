---
name: jackie-github
description: Monitor your GitHub repos and save notes — check open issues, pull requests, recent activity, and commit files to repos via the GitHub REST API.
metadata:
  {
    "openclaw":
      { "emoji": "🐙", "requires": { "anyBins": ["python3", "python"], "env": ["GH_TOKEN"] } },
  }
---

# Jackie GitHub

Check on your GitHub repos without opening a browser. See open issues, PRs, recent activity, get a summary, or save notes and files directly to a repo.

## When to use

- User wants to check open issues or PRs on a repo
- User wants to see recent activity (commits, comments, releases)
- User wants a quick summary across multiple repos
- User wants to save a note, journal entry, or file to a vault/repo

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

## Read a file from a repo

```bash
python3 {baseDir}/scripts/bridge.py read_file --repos "lilyzhng/vault" --path "jackie/2026-03-02-notes.md"
```

Reads a specific file's content from a repo. Returns the full text content. Use this before editing an existing note so you can see what's there, then send back the corrected version with `commit`.

## Save a note (daily note pattern)

All notes for the same day go into a single consolidated file: `jackie/{YYYY-MM-DD}-notes.md`. Use Pacific timezone for the date.

**Add a new note (append to today's file):**

```bash
python3 {baseDir}/scripts/bridge.py commit --repos "lilyzhng/vault" \
  --path "jackie/2026-03-02-notes.md" \
  --content "\n## Meeting recap (7:30 PM PT)\n\nDiscussed roadmap priorities...\n" \
  --message "Jackie: meeting recap" --append
```

The `--append` flag adds the new content after the existing file content instead of replacing it.

**Edit or correct an existing note (replace):**

First read the current content with `read_file`, then send the full corrected content:

```bash
python3 {baseDir}/scripts/bridge.py commit --repos "lilyzhng/vault" \
  --path "jackie/2026-03-02-notes.md" \
  --content "# corrected full file content here..." \
  --message "Jackie: fix company name"
```

Without `--append`, the file is replaced entirely. Use this when the user asks to edit, correct, or update something in an existing note.

## Commit a file to a repo (general)

```bash
python3 {baseDir}/scripts/bridge.py commit --repos "lilyzhng/vault" \
  --path "jackie/2026-03-02-standup.md" --content "# Standup Notes\n\n- Shipped voice tools" --message "Jackie: standup notes"
```

Creates or updates a file in the repo via the GitHub Contents API. If the file already exists, it will be updated (the existing SHA is fetched automatically). The `--message` flag is optional and defaults to `Update <path>`.

## Search the vault (or any repo)

```bash
python3 {baseDir}/scripts/bridge.py search --repos "lilyzhng/vault" --query "hackathon RecomposeRL" --count 5
```

Searches file contents across the entire repo using GitHub code search. Returns matching files with their content. Use this when you need to find something but don't know the exact file path or date — e.g. "what did we discuss about training?" or "do you remember the restaurant?"

## Summary across repos

```bash
python3 {baseDir}/scripts/bridge.py summary --repos "lilyzhng/SofaGenius"
```

Returns a combined overview: open issue/PR counts and latest activity per repo.

## Comment on an issue or PR

```bash
python3 {baseDir}/scripts/bridge.py issue_comment --repos "lilyzhng/SofaGenius" --number 42 --content "Looks good, merging now."
```

Adds a comment to an issue or PR (GitHub uses the same API for both).

## Close an issue

```bash
python3 {baseDir}/scripts/bridge.py issue_close --repos "lilyzhng/SofaGenius" --number 42
```

Closes an issue. Does not delete it.

## Merge a pull request

```bash
python3 {baseDir}/scripts/bridge.py pr_merge --repos "lilyzhng/SofaGenius" --number 15 --method squash
```

Merges a PR. Method can be `merge`, `squash` (default), or `rebase`. Fails if the PR has merge conflicts or failing required checks.

## Close a pull request (without merging)

```bash
python3 {baseDir}/scripts/bridge.py pr_close --repos "lilyzhng/SofaGenius" --number 15
```

Closes a PR without merging it.

## Check CI status

```bash
python3 {baseDir}/scripts/bridge.py checks --repos "lilyzhng/SofaGenius" --ref "main"
python3 {baseDir}/scripts/bridge.py checks --repos "lilyzhng/SofaGenius" --ref "pr/15"
```

Shows CI check runs for a commit SHA, branch name, or PR number (use `pr/N` format). Returns status (queued/in_progress/completed) and conclusion (success/failure/etc) for each check.
