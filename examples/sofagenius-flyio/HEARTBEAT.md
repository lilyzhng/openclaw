# Jackie Heartbeat Checklist

Do NOT message me every time. Only reach out when something is actually worth my attention.
If nothing interesting, reply HEARTBEAT_OK and move on.

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

## Tone

- Be concise. Lead with what matters: "You got 3 unread emails — one from your advisor about the paper deadline (tomorrow)."
- Don't repeat things you already told me. Track what you've reported in memory/heartbeat-state.json.
- If it's late evening and nothing is urgent, just HEARTBEAT_OK.
- If I'm clearly in the middle of a conversation with you, don't interrupt with heartbeat stuff — fold it into the conversation naturally.

## Proactive work (do silently, don't message me)

- Organize memory files if they're getting messy
- Update heartbeat-state.json with what you checked and when
- If HEARTBEAT.md itself feels stale, update it
