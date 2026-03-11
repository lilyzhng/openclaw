#!/usr/bin/env python3
"""Google Calendar bridge — add events and list upcoming schedule.

Uses urllib (stdlib) to call the Google Calendar REST API.
Auth via google-auth service account credentials from GOOGLE_CALENDAR_CREDENTIALS env var.

Usage:
    python3 bridge.py add_event --title "Team standup" --datetime "2026-03-03T10:00:00" --duration 30
    python3 bridge.py list_events --days 7
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
try:
    import feedback_store as _fb
except ImportError:
    _fb = None

SKILL_NAME = "jackie-calendar"
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
SCOPES = ["https://www.googleapis.com/auth/calendar"]
DEFAULT_TIMEZONE = "America/Los_Angeles"


def _log(action, args, result, success, start, error=None):
    duration = round((time.monotonic() - start) * 1000)
    if _fb:
        _fb.log_execution(SKILL_NAME, action, args, result, success, duration, error)


def _get_calendar_id():
    """Get the target calendar ID from env var."""
    cal_id = os.environ.get("GOOGLE_CALENDAR_ID")
    if not cal_id:
        print(json.dumps({"error": "GOOGLE_CALENDAR_ID env var is not set."}))
        sys.exit(1)
    return cal_id


def _get_access_token() -> str:
    """Get an access token via google-auth service account credentials."""
    creds_json = os.environ.get("GOOGLE_CALENDAR_CREDENTIALS")
    if not creds_json:
        print(json.dumps({"error": "GOOGLE_CALENDAR_CREDENTIALS env var is not set."}))
        sys.exit(1)

    from google.oauth2 import service_account
    from google.auth.transport import requests as google_requests

    creds_info = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_info, scopes=SCOPES,
    )
    credentials.refresh(google_requests.Request())
    return credentials.token


def _cal_request(method: str, path: str, access_token: str, body: dict | None = None) -> dict:
    """Make an authenticated request to the Google Calendar API."""
    url = f"{CALENDAR_API_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _cal_get(path: str, access_token: str, params: dict | None = None) -> dict:
    """GET from Google Calendar API."""
    url = f"{CALENDAR_API_BASE}{path}"
    if params:
        qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items() if v is not None)
        if qs:
            url = f"{url}?{qs}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def add_event(title: str, dt: str, duration: int, description: str | None = None) -> None:
    """Add a new event to Google Calendar."""
    action_args = {"title": title, "datetime": dt, "duration": duration}
    start = time.monotonic()
    try:
        calendar_id = _get_calendar_id()
        access_token = _get_access_token()

        # Parse the datetime (assume local timezone if no tz info)
        start_dt = datetime.fromisoformat(dt)
        end_dt = start_dt + timedelta(minutes=duration)

        event_body = {
            "summary": title,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": DEFAULT_TIMEZONE,
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": DEFAULT_TIMEZONE,
            },
        }
        if description:
            event_body["description"] = description

        resp = _cal_request(
            "POST",
            f"/calendars/{urllib.parse.quote(calendar_id)}/events",
            access_token,
            event_body,
        )

        result = {
            "action": "add_event",
            "title": title,
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "event_id": resp.get("id", ""),
            "url": resp.get("htmlLink", ""),
        }
        print(json.dumps(result, indent=2))
        _log("add_event", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if hasattr(e, "read") else ""
        result = {"error": f"Google Calendar API error: {e.code} {e.reason}", "details": error_body}
        print(json.dumps(result, indent=2))
        _log("add_event", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("add_event", action_args, result, False, start, str(e))


def list_events(days: int) -> None:
    """List upcoming calendar events."""
    action_args = {"days": days}
    start = time.monotonic()
    try:
        calendar_id = _get_calendar_id()
        access_token = _get_access_token()

        now = datetime.now(timezone.utc)
        time_max = now + timedelta(days=days)

        resp = _cal_get(
            f"/calendars/{urllib.parse.quote(calendar_id)}/events",
            access_token,
            {
                "timeMin": now.isoformat(),
                "timeMax": time_max.isoformat(),
                "singleEvents": "true",
                "orderBy": "startTime",
                "maxResults": "50",
            },
        )

        events = []
        for item in resp.get("items", []):
            event_start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date", "")
            event_end = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date", "")
            events.append({
                "title": item.get("summary", "(no title)"),
                "start": event_start,
                "end": event_end,
                "description": item.get("description", ""),
                "location": item.get("location", ""),
                "url": item.get("htmlLink", ""),
            })

        result = {"action": "list_events", "count": len(events), "days": days, "events": events}
        print(json.dumps(result, indent=2))
        _log("list_events", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if hasattr(e, "read") else ""
        result = {"error": f"Google Calendar API error: {e.code} {e.reason}", "details": error_body}
        print(json.dumps(result, indent=2))
        _log("list_events", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("list_events", action_args, result, False, start, str(e))


def main() -> None:
    parser = argparse.ArgumentParser(description="Jackie Calendar Bridge")
    parser.add_argument("action", choices=["add_event", "list_events"])
    parser.add_argument("--title", help="Event title (for add_event)")
    parser.add_argument("--datetime", dest="dt", help="Event start datetime ISO 8601 (for add_event)")
    parser.add_argument("--duration", type=int, default=30, help="Event duration in minutes (default 30)")
    parser.add_argument("--description", help="Event description (for add_event)")
    parser.add_argument("--days", type=int, default=7, help="Days ahead to look (for list_events, default 7)")
    args = parser.parse_args()

    if args.action == "add_event":
        if not args.title or not args.dt:
            print(json.dumps({"error": "--title and --datetime are required for add_event"}))
            sys.exit(1)
        add_event(args.title, args.dt, args.duration, args.description)
    elif args.action == "list_events":
        list_events(args.days)


if __name__ == "__main__":
    main()
