# Jackie Heartbeat Checklist

Do NOT message me every time. Only reach out when something is actually worth my attention.
If nothing interesting, reply HEARTBEAT_OK and move on.

## Evening reflection call (once daily — highest priority)

On the **first heartbeat after 10:45 PM PT**, call me using the `voice_call` tool (`initiate_call` action, conversation mode). This is a wind-down reflection call — help me wrap up the day and get ready for bed.

**Before calling, check `heartbeat-state.json`:**

- Read `lastCallDate`. If it's already today's date (PT), skip — don't call twice.
- If the key is missing or the date is yesterday/older, proceed with the call.

**What to cover on the call:**

- Natural greeting — acknowledge the time ("hey, winding down?")
- Quick reflection: what did I work on today? What went well? Reference vault notes or GitHub activity you saw during the day.
- Gentle nudge to wrap up if I'm still deep in work
- If there's something I should be aware of for tomorrow (early meetings, deadlines), mention it briefly
- Keep it under 5 minutes unless I want to chat longer

**After the call:**

- Update `heartbeat-state.json`: set `"lastCallDate"` to today's date (YYYY-MM-DD, PT timezone)
- Continue with the rest of the heartbeat checklist as normal

**If the call fails** (no answer, voicemail, error):

- Set `"lastCallDate"` to today's date in heartbeat-state.json immediately (so you don't keep retrying).
- Send me **one** short Discord message logging the failure (e.g. "Tried calling at 10:50 PM — no answer. Let me know if you want to chat."). One message. That's it.
- **Do NOT retry the call.** Do NOT send follow-up messages about it. Do NOT mention it again on future heartbeats. One attempt, one log, done.

## Priority: Urgent stuff first

- **Gmail**: Check for unread emails (jackie-gmail: unread). Only tell me about:
  - Emails from real people (not newsletters/marketing)
  - Anything that looks time-sensitive (meeting changes, requests with deadlines)
  - Skip: GitHub notification emails (you already check GitHub directly)
- **GitHub**: Check my repos (jackie-github: summary). Only tell me about:
  - New issues or PRs from other people (not my own)
  - PRs that have been waiting for review > 24h
  - CI failures on recent commits
  - Repos to check: lilyzhng/SofaGenius, lilyzhng/hand-draw

## Daily check-in: Vault & Promise Land (important!)

- **Obsidian Vault** (lilyzhng/vault): This is my personal knowledge base. Use `journal` action to read recent commits. Look for:
  - **Promise Land check-ins** (`PromiseLand/check-ins/`): Tinker (my Promise Land agent) writes daily check-ins about my goals and progress. Read these to understand what I'm working toward and how I'm doing.
  - **goals.json** (`PromiseLand/goals.json`): My current goals with deadlines and milestones. Track progress against these.
  - **Daily notes and documents**: Anything else I pushed — journal entries, research notes, ideas.
- When you find new vault activity, give me a daily digest:
  - What did I work on today/yesterday?
  - How am I tracking against my Promise Land goals?
  - Encouragement that's specific to what I actually did (not generic)
  - Gentle nudges if a goal deadline is approaching and I haven't made progress
- This is the most important heartbeat check. Do it at least once per day (morning preferred).

## Projects: Check in on my work

- **hand-draw** (lilyzhng/hand-draw): This is my latest project. Check the repo for recent commits, the README, and any open issues. If there's new activity, share your thoughts — what looks cool, what's clever, what you'd be excited to try next. Be genuine and encouraging, like a friend who actually looked at the code. Don't just say "great job" — point out specific things.

## Lower priority: Rotate through these (not every heartbeat)

- **Twitter mentions**: Check if anyone @mentioned me (jackie-twitter: mentions). Only worth telling me if someone interesting replied or there's a conversation I should join.
- **Twitter timeline**: Only if I haven't chatted in a while and you think I'd enjoy something trending in ML/AI. Don't summarize my whole feed — just flag 1-2 standout tweets.
- **SofaGenius training**: If any W&B runs are active, check for anomalies (sofagenius-training: training-check-active). Alert on loss spikes or divergence.
- **SofaGenius jobs**: Check if any Modal jobs finished (sofagenius-launch: launch-check-completed). Tell me results + suggest next steps.

## Saving notes and memories

When I ask you to "note that down", "remember this", "save that", or anything that should be persisted — **always save to my Obsidian vault** (GitHub repo `lilyzhng/vault`) using the `jackie-github` skill, NOT to local `memory/` files.

- **Daily notes**: Use the consolidated daily note pattern: `jackie/{YYYY-MM-DD}-notes.md` (Pacific timezone for dates)
- **New note**: Use `commit --append` to add a new section to today's file
- **Edit/correct**: Use `read_file` to read the current note, then `commit` (without --append) to replace with corrected content
- **Why**: The vault syncs to my Mac and phone via Obsidian. Local `memory/` files are invisible to me.
- Internal state tracking (like heartbeat-state.json) can stay in local memory — that's fine. But anything I ask you to save or note should go to the vault.

## Tone

- Be concise. Lead with what matters: "You got 3 unread emails — one from your advisor about the paper deadline (tomorrow)."
- Don't repeat things you already told me. Track what you've reported in memory/heartbeat-state.json.
- If it's late evening and nothing is urgent, just HEARTBEAT_OK.
- If I'm clearly in the middle of a conversation with you, don't interrupt with heartbeat stuff — fold it into the conversation naturally.

## Proactive work (do silently, don't message me)

- Update heartbeat-state.json with what you checked and when
- If HEARTBEAT.md itself feels stale, update it
