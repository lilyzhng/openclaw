---
name: jackie-gmail
description: Check your Gmail inbox for recent and unread emails, or search by keyword. Read-only — never modifies, deletes, or sends emails.
metadata: {"openclaw": {"emoji": "📧", "requires": {"anyBins": ["python3", "python"], "env": ["GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"]}}}
---

# Jackie Gmail

Scan your Gmail inbox without opening a browser. Read-only IMAP access — never modifies or deletes emails.

## When to use

- User wants to check their recent emails
- User wants to see only unread emails
- User wants to search for emails by keyword, sender, or subject

## Check recent emails

```bash
python3 {baseDir}/scripts/bridge.py inbox --count 10
```

Returns the most recent emails with from, subject, date, and body preview.

## Check unread emails only

```bash
python3 {baseDir}/scripts/bridge.py unread --count 10
```

Returns only unread emails, newest first.

## Search emails

```bash
python3 {baseDir}/scripts/bridge.py search --query "from:github.com" --count 10
```

Searches using IMAP search syntax. Common patterns:
- `from:sender@example.com` — emails from a specific sender
- `subject:urgent` — emails with a keyword in the subject
- `after:2026-02-01` — emails after a date
- `is:unread subject:invoice` — combine filters
