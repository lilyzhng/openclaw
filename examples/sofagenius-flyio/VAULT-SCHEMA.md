# Jackie Vault Schema

**Purpose:** Define a clean, structured memory system for Jackie's vault (`lilyzhng/vault/jackie/`).

## Current Problems

1. Everything is flat in `jackie/` — conversations, notes, call summaries, action items all mixed
2. `MEMORY.md` contains behavioral rules (should be in SOUL.md), not actual memory
3. No separation between short/mid/long-term memory
4. No structured action items tracking
5. No consolidation process — notes accumulate but never get distilled

## New Structure

```
vault/jackie/
│
├── config/                          ← BEHAVIOR (how Jackie acts)
│   ├── AGENTS.md                    ← behavior rules, workflows
│   ├── HEARTBEAT.md                 ← proactive check config
│   ├── SOUL.md                      ← personality, identity, communication style
│   └── TOOLS.md                     ← tool gotchas, integration notes
│
├── conversations/                   ← RAW LOGS (what happened)
│   ├── 2026-03-10-discord.md        ← Discord conversation notes
│   ├── 2026-03-10-call-summary.md   ← Phone call transcripts
│   ├── 2026-03-10-call-2.md         ← Second call that day
│   └── ...
│
├── memory/                          ← STRUCTURED MEMORY (what Jackie knows)
│   ├── short-term.md                ← Today's active context (overwritten daily)
│   ├── mid-term/                    ← Active projects, open loops, decisions in progress
│   │   ├── openclaw-vm-autonomy.md  ← Active project: VM autonomy work
│   │   ├── training-grpo.md         ← Active project: GRPO training
│   │   └── ...
│   └── long-term.md                 ← Durable facts about Lily (preferences, goals, people, history)
│
├── action-items.md                  ← WHAT NEEDS DOING (single source of truth)
│
├── .learnings/                      ← SELF-IMPROVEMENT (errors, corrections, feature gaps)
│   ├── ERRORS.md
│   ├── LEARNINGS.md
│   └── FEATURE_REQUESTS.md
│
└── archive/                         ← OLD CONVERSATIONS (moved after 2 weeks)
    └── 2026-02/
        └── ...
```

## What Lives Where

### `config/` — How Jackie Behaves

- **SOUL.md** — personality, communication style, behavioral rules
  - The "adaptive communication" content currently in MEMORY.md belongs here
- **AGENTS.md** — workflows, session-start routine, tool usage patterns
- **HEARTBEAT.md** — proactive check config
- **TOOLS.md** — tool capabilities, gotchas learned from experience

### `conversations/` — Raw Logs

- One file per conversation per day
- Naming: `{YYYY-MM-DD}-{type}.md` where type is `discord`, `call-summary`, `whatsapp`, etc.
- Jackie writes here during/after each conversation
- These are **append-only** — never edit old conversations
- Moved to `archive/` after 2 weeks (keeps vault fast to search)

### `memory/` — What Jackie Knows

**`short-term.md`** — Today's active context

- What Lily is working on right now
- Things mentioned in today's conversations
- Temporary notes that may not matter tomorrow
- **Overwritten at the start of each day** (yesterday's short-term either gets promoted or discarded)

**`mid-term/`** — Active projects and open loops

- One file per active project/topic
- Decisions in progress, things being tracked
- Open questions waiting for answers
- **Reviewed weekly** — completed projects get archived, key insights promoted to long-term

**`long-term.md`** — Durable facts

- Lily's preferences (communication style, schedule, tools she uses)
- Key people (who they are, relationship)
- Recurring goals and values
- Important dates
- Things Lily explicitly said to remember
- **Rarely changes** — only add when something is truly durable

### `action-items.md` — What Needs Doing

Single file with sections:

```markdown
# Action Items

## Urgent (do today)

- [ ] ...

## This Week

- [ ] ...

## Someday / Waiting

- [ ] ...

## Done (recent)

- [x] 2026-03-10: ...
```

- Jackie adds items from conversations
- Jackie checks off items when done
- Lily can add/edit items in Obsidian
- **Reviewed every heartbeat** — nudge Lily about overdue items

### `.learnings/` — Self-Improvement

(Already defined in the self-improvement section)

## Memory Consolidation Process

### After Every Conversation

1. Save raw conversation to `conversations/{date}-{type}.md`
2. Update `memory/short-term.md` with anything noteworthy
3. Add any action items to `action-items.md`
4. If a new project/topic emerged, create a file in `memory/mid-term/`

### Daily (first heartbeat of the day)

1. Review yesterday's `short-term.md`
2. Promote anything lasting to `mid-term/` or `long-term.md`
3. Start fresh `short-term.md` for today
4. Check `action-items.md` for overdue items

### Weekly (Sunday heartbeat)

1. Review all `mid-term/` files
2. Archive completed projects
3. Promote key insights to `long-term.md`
4. Review `.learnings/` for patterns to promote
5. Clean up `conversations/` — move files older than 2 weeks to `archive/`

## Migration Plan

Move existing flat files to the new structure:

| Current                               | New location                                           |
| ------------------------------------- | ------------------------------------------------------ |
| `jackie/MEMORY.md` (behavioral rules) | `jackie/config/SOUL.md` (merge with existing)          |
| `jackie/MEMORY.md` (facts about Lily) | `jackie/memory/long-term.md`                           |
| `jackie/*-notes.md`                   | `jackie/conversations/*-discord.md`                    |
| `jackie/*-call-summary.md`            | `jackie/conversations/*-call-summary.md`               |
| `jackie/VAULT-SETUP.md`               | `jackie/archive/` or delete (superseded by design doc) |
