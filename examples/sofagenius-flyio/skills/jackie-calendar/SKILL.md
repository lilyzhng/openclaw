---
name: jackie-calendar
description: Manage Google Calendar — add events, list upcoming events, and check your schedule. Uses the Google Calendar REST API with service account auth.
metadata:
  {
    "openclaw":
      {
        "emoji": "📅",
        "requires":
          {
            "anyBins": ["python3", "python"],
            "env": ["GOOGLE_CALENDAR_CREDENTIALS", "GOOGLE_CALENDAR_ID"],
          },
      },
  }
---

# Jackie Calendar

Add events and check your schedule on Google Calendar without opening a browser.

## When to use

- User wants to add a meeting, reminder, or event to their calendar
- User wants to check what's coming up today or this week
- User asks about their schedule or availability

## Add a calendar event

```bash
python3 {baseDir}/scripts/bridge.py add_event --title "Team standup" --datetime "2026-03-03T10:00:00" --duration 30
```

Creates a new event on the calendar. `--datetime` is ISO 8601 format, `--duration` is in minutes (default 30). Optional `--description` for event body. The timezone defaults to America/Los_Angeles.

## List upcoming events

```bash
python3 {baseDir}/scripts/bridge.py list_events --days 7
```

Lists upcoming events. Use `--days` to control how far ahead to look (default 7). Returns event titles, times, and descriptions.
