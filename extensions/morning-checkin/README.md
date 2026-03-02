# @openclaw/morning-checkin

Scheduled morning voice call check-in with Obsidian vault transcript sync.

## How it works

1. A **cron job** fires at your configured time (e.g. 8:00 AM)
2. An **isolated agent turn** runs and uses the `voice_call` tool to call your phone
3. The agent conducts a **morning check-in conversation** (priorities, tasks, blockers)
4. After the call, the agent writes a **cleaned markdown note** to your Obsidian vault
5. The vault is **git committed and pushed** so it syncs across devices

## Prerequisites

- **voice-call plugin** configured with Twilio or Telnyx (provider, fromNumber, toNumber)
- **OpenAI API key** for STT (speech-to-text during the call) and TTS (text-to-speech)
- **Obsidian vault** as a git repo (for note sync)

## Install

```bash
openclaw plugins install @openclaw/morning-checkin
```

## Config

Add to your OpenClaw config under `plugins.entries.morning-checkin.config`:

```json5
{
  enabled: true,
  time: "08:00",           // 24h format
  tz: "America/New_York",  // IANA timezone
  toNumber: "+15550001234", // your phone (or omit to use voice-call default)

  // Obsidian vault
  vaultPath: "/path/to/your/obsidian-vault",
  vaultSubdir: "daily-checkins",  // notes go here
  gitSync: true,                   // auto commit+push

  // Optional
  maxCallDurationMin: 15,
  briefingPrompt: "Focus on my startup tasks and investor follow-ups.",
}
```

## CLI

```bash
# Show current config
openclaw morning-checkin config

# Print setup instructions (cron job creation)
openclaw morning-checkin setup

# Trigger a check-in call right now (prints the agent prompt)
openclaw morning-checkin run
```

## Setting up the cron job

After configuring the plugin, create the scheduled job:

```bash
openclaw cron add \
  --name "morning-checkin" \
  --cron "0 8 * * *" \
  --tz "America/New_York" \
  --session-target isolated \
  --message "Run the morning check-in. Use voice_call to call me, have the conversation, then write the daily note to my Obsidian vault."
```

Or let the agent set it up by telling it: "Set up my morning check-in call for 8am Eastern."

## Output

Each check-in produces a markdown file like `daily-checkins/2026-03-02.md`:

```markdown
---
date: 2026-03-02
type: morning-checkin
---

# Daily Check-in — 2026-03-02

## Summary
Discussed Q1 priorities and the upcoming product demo. Decided to postpone
the database migration until after the demo.

## Action Items
- [ ] Prepare demo slides by Wednesday
- [ ] Follow up with design team on new mockups
- [ ] Review PR #1234

## Decisions Made
- Postpone DB migration to next sprint
- Use the staging environment for the demo

## Notes
- Team standup moved to 10am this week
- New hire starting Monday

## Raw Highlights
- "Let's focus on the demo first, everything else can wait"
- "The staging env should be stable enough for the demo"
```
