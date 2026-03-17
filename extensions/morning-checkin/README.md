# @openclaw/morning-checkin

Scheduled morning voice call check-in.

## How it works

1. A **cron job** fires at your configured time (e.g. 8:00 AM)
2. An **isolated agent turn** runs and uses the `voice_call` tool to call your phone
3. The agent conducts a **morning check-in conversation** (priorities, tasks, blockers)
4. After the call, the agent posts a **summary in chat** with action items and decisions

## Prerequisites

- **voice-call plugin** configured with Twilio or Telnyx (provider, fromNumber, toNumber)
- **OpenAI API key** for STT (speech-to-text during the call) and TTS (text-to-speech)

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
  maxCallDurationMin: 15,  // safety cap (default: 15)
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
  --message "Run the morning check-in. Use voice_call to call me and have the conversation."
```

Or let the agent set it up by telling it: "Set up my morning check-in call for 8am Eastern."
