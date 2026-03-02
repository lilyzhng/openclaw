#!/usr/bin/env python3
"""Standalone Gmail bridge — checks inbox, unread, and searches via IMAP.

Uses imaplib + email (Python stdlib). No extra dependencies.
Read-only: uses IMAP readonly=True, never modifies, deletes, or sends emails.

Execution telemetry is auto-captured to the feedback store so SofaGenius
can learn from operational patterns over time.

Usage:
    python3 bridge.py inbox --count 10
    python3 bridge.py unread --count 10
    python3 bridge.py search --query "from:github.com" --count 10
"""

import argparse
import email
import email.header
import email.utils
import imaplib
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
try:
    import feedback_store as _fb
except ImportError:
    _fb = None

SKILL_NAME = "jackie-gmail"
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
BODY_PREVIEW_LEN = 500


def _get_credentials():
    address = os.environ.get("GMAIL_ADDRESS")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not address or not password:
        print(json.dumps({
            "error": "GMAIL_ADDRESS and GMAIL_APP_PASSWORD env vars are required. "
                     "Generate an App Password at https://myaccount.google.com/apppasswords"
        }))
        sys.exit(1)
    return address, password


def _connect():
    """Connect to Gmail IMAP in read-only mode."""
    address, password = _get_credentials()
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(address, password)
    mail.select("INBOX", readonly=True)
    return mail


def _decode_header(raw):
    """Decode a MIME-encoded header value."""
    if not raw:
        return ""
    parts = email.header.decode_header(raw)
    decoded = []
    for content, charset in parts:
        if isinstance(content, bytes):
            decoded.append(content.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(content)
    return " ".join(decoded)


def _extract_body(msg):
    """Extract plain text body from email, truncated to preview length."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain" and part.get("Content-Disposition") != "attachment":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    text = payload.decode(charset, errors="replace")
                    return text[:BODY_PREVIEW_LEN]
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            return text[:BODY_PREVIEW_LEN]
    return ""


def _parse_email(raw_bytes):
    """Parse raw email bytes into a clean dict."""
    msg = email.message_from_bytes(raw_bytes)
    date_str = msg.get("Date", "")
    parsed_date = email.utils.parsedate_to_datetime(date_str) if date_str else None

    return {
        "from": _decode_header(msg.get("From", "")),
        "to": _decode_header(msg.get("To", "")),
        "subject": _decode_header(msg.get("Subject", "")),
        "date": parsed_date.isoformat() if parsed_date else date_str,
        "body_preview": _extract_body(msg),
    }


def _fetch_emails(mail, msg_ids, count):
    """Fetch and parse a list of email IDs (newest first)."""
    # msg_ids come space-separated, take the last `count` (newest)
    id_list = msg_ids.split()
    id_list = id_list[-count:] if len(id_list) > count else id_list
    id_list.reverse()  # newest first

    emails = []
    for mid in id_list:
        _, data = mail.fetch(mid, "(RFC822)")
        if data and data[0] and isinstance(data[0], tuple):
            parsed = _parse_email(data[0][1])
            emails.append(parsed)
    return emails


def _build_imap_search(query: str) -> str:
    """Convert user-friendly search syntax to IMAP search criteria.

    Supports:
        from:addr     -> FROM "addr"
        subject:word  -> SUBJECT "word"
        after:date    -> SINCE "01-Jan-2026"
        before:date   -> BEFORE "01-Jan-2026"
        is:unread     -> UNSEEN
        bare words    -> TEXT "word"
    """
    parts = []
    tokens = query.split()
    for token in tokens:
        if ":" in token:
            key, val = token.split(":", 1)
            key = key.lower()
            if key == "from":
                parts.append(f'FROM "{val}"')
            elif key == "subject":
                parts.append(f'SUBJECT "{val}"')
            elif key == "to":
                parts.append(f'TO "{val}"')
            elif key == "after" or key == "since":
                try:
                    d = datetime.strptime(val, "%Y-%m-%d")
                    parts.append(f'SINCE "{d.strftime("%d-%b-%Y")}"')
                except ValueError:
                    parts.append(f'TEXT "{val}"')
            elif key == "before":
                try:
                    d = datetime.strptime(val, "%Y-%m-%d")
                    parts.append(f'BEFORE "{d.strftime("%d-%b-%Y")}"')
                except ValueError:
                    parts.append(f'TEXT "{val}"')
            elif key == "is" and val.lower() == "unread":
                parts.append("UNSEEN")
            else:
                parts.append(f'TEXT "{token}"')
        else:
            parts.append(f'TEXT "{token}"')
    return " ".join(parts) if parts else "ALL"


def _log(action, args, result, success, start, error=None):
    duration = round((time.monotonic() - start) * 1000)
    if _fb:
        _fb.log_execution(SKILL_NAME, action, args, result, success, duration, error)


def inbox(count: int) -> None:
    action_args = {"count": count}
    start = time.monotonic()
    try:
        mail = _connect()
        _, data = mail.search(None, "ALL")
        msg_ids = data[0].decode() if data[0] else ""
        if not msg_ids:
            result = {"action": "inbox", "count": 0, "emails": []}
            print(json.dumps(result, indent=2))
            _log("inbox", action_args, result, True, start)
            mail.logout()
            return

        emails = _fetch_emails(mail, msg_ids, count)
        mail.logout()

        result = {"action": "inbox", "count": len(emails), "emails": emails}
        print(json.dumps(result, indent=2))
        _log("inbox", action_args, result, True, start)
    except imaplib.IMAP4.error as e:
        result = {"error": f"IMAP error: {e}"}
        print(json.dumps(result, indent=2))
        _log("inbox", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("inbox", action_args, result, False, start, str(e))


def unread(count: int) -> None:
    action_args = {"count": count}
    start = time.monotonic()
    try:
        mail = _connect()
        _, data = mail.search(None, "UNSEEN")
        msg_ids = data[0].decode() if data[0] else ""
        if not msg_ids:
            result = {"action": "unread", "count": 0, "emails": []}
            print(json.dumps(result, indent=2))
            _log("unread", action_args, result, True, start)
            mail.logout()
            return

        emails = _fetch_emails(mail, msg_ids, count)
        mail.logout()

        result = {"action": "unread", "count": len(emails), "emails": emails}
        print(json.dumps(result, indent=2))
        _log("unread", action_args, result, True, start)
    except imaplib.IMAP4.error as e:
        result = {"error": f"IMAP error: {e}"}
        print(json.dumps(result, indent=2))
        _log("unread", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("unread", action_args, result, False, start, str(e))


def search_emails(query: str, count: int) -> None:
    action_args = {"query": query, "count": count}
    start = time.monotonic()
    try:
        mail = _connect()
        imap_criteria = _build_imap_search(query)
        _, data = mail.search(None, imap_criteria)
        msg_ids = data[0].decode() if data[0] else ""
        if not msg_ids:
            result = {"action": "search", "query": query, "imap_criteria": imap_criteria,
                      "count": 0, "emails": []}
            print(json.dumps(result, indent=2))
            _log("search", action_args, result, True, start)
            mail.logout()
            return

        emails = _fetch_emails(mail, msg_ids, count)
        mail.logout()

        result = {"action": "search", "query": query, "imap_criteria": imap_criteria,
                  "count": len(emails), "emails": emails}
        print(json.dumps(result, indent=2))
        _log("search", action_args, result, True, start)
    except imaplib.IMAP4.error as e:
        result = {"error": f"IMAP error: {e}"}
        print(json.dumps(result, indent=2))
        _log("search", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("search", action_args, result, False, start, str(e))


def main() -> None:
    parser = argparse.ArgumentParser(description="Jackie Gmail Bridge")
    parser.add_argument("action", choices=["inbox", "unread", "search"])
    parser.add_argument("--query", help="Search query (required for search)")
    parser.add_argument("--count", type=int, default=10, help="Number of emails (default 10)")
    args = parser.parse_args()

    if args.action == "inbox":
        inbox(args.count)
    elif args.action == "unread":
        unread(args.count)
    elif args.action == "search":
        if not args.query:
            parser.error("--query required for search")
        search_emails(args.query, args.count)


if __name__ == "__main__":
    main()
