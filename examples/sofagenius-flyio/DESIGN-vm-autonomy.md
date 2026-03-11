# Design Doc: Jackie VM Autonomy

**Status:** Draft → Ready for Implementation
**Date:** 2026-03-10
**Author:** Lily + Claude
**Goal:** Give Jackie the ability to self-modify, install tools, and manage memory — without rebuilding Docker.

---

## Key Decisions (from discussion)

1. **Vault is the single source of truth** — AGENTS.md, HEARTBEAT.md, SOUL.md, memory all live in the vault. Lily can edit in Obsidian, push, and Jackie auto-pulls.
2. **Jackie has full self-modification autonomy** — can edit his own behavior rules and restart services without asking. No approval needed.
3. **Hybrid sync cadence** — pull on conversation start, push on conversation end/compaction, pull+push on every heartbeat (30min fallback).
4. **Chromium pre-installed in Dockerfile** — one-time build cost, instant availability on every boot.
5. **Post-action notification** — Jackie notifies Lily briefly after installing packages or modifying config ("btw I just installed X"). No pre-approval, just awareness.

---

## Problem Statement

Every change to Jackie's behavior, skills, or tools requires:

1. Edit files locally
2. Rebuild Docker image
3. Push to Fly.io
4. Wait 10-30 minutes for deployment

This makes Jackie dependent on Lily for all evolution. Jackie cannot:

- Install a browser when he needs one
- Add a new skill during conversation
- Fix his own AGENTS.md when behavior is wrong
- Keep memory in sync across Discord and Phone sessions

## Design Principle

**Separate infrastructure (rarely changes) from brain (changes often).**

| Layer                                               | Lives in                                          | Who changes it | How often     |
| --------------------------------------------------- | ------------------------------------------------- | -------------- | ------------- |
| Infrastructure (Node, Python, OpenClaw, supervisor) | Docker image                                      | Lily (rebuild) | Rarely        |
| Brain (AGENTS.md, SOUL.md, HEARTBEAT.md, skills)    | GitHub vault → synced to `/data`                  | Jackie + Lily  | Often         |
| Memory (MEMORY.md, daily notes, conversations)      | GitHub vault → synced to `/data`                  | Jackie + Lily  | Every session |
| User-installed packages (chromium, etc.)            | Docker (pre-installed) + recovery list on `/data` | Jackie         | As needed     |

---

## Architecture

```
Fly.io VM
├── Docker image (immutable, rebuilt rarely)
│   ├── Node 22, Python 3, OpenClaw binary
│   ├── supervisor, ngrok, chromium, core Python packages
│   └── /opt/sofagenius-skills-default/    ← factory defaults (fallback only)
│
├── /data/ (persistent volume 5GB, survives restarts + deploys)
│   ├── vault/                             ← git clone of lilyzhng/vault (SOURCE OF TRUTH)
│   │   └── jackie/
│   │       ├── config/
│   │       │   ├── AGENTS.md              ← behavior rules (Jackie + Lily edit)
│   │       │   ├── HEARTBEAT.md           ← proactive check config
│   │       │   └── SOUL.md               ← personality (Lily edits in Obsidian)
│   │       ├── skills/                    ← skill definitions (backed up)
│   │       │   └── jackie-browser/
│   │       ├── MEMORY.md
│   │       ├── 2026-03-10-notes.md
│   │       └── ...
│   ├── skills/                            ← live skills directory (symlinked/synced from vault)
│   │   ├── jackie-github/
│   │   ├── jackie-calendar/
│   │   └── ... (Jackie can add new ones)
│   ├── packages/
│   │   ├── apt-packages.txt              ← user-installed apt packages
│   │   ├── pip-packages.txt              ← user-installed pip packages
│   │   └── npm-packages.txt              ← user-installed npm global packages
│   └── openclaw state (sessions, etc.)
│
└── entrypoint.sh (runs on every boot)
    ├── 1. Clone or pull vault
    ├── 2. Symlink vault config → workspace
    ├── 3. Initialize /data/skills from vault + defaults
    ├── 4. Restore user-installed packages
    └── 5. Start supervisor
```

### Sync Flow

```
Lily edits in Obsidian → auto-push to GitHub
                                ↓
              Jackie pulls on: conversation start / heartbeat
                                ↓
                      /data/vault/ updated
                                ↓
              Symlinks point workspace → vault files
                                ↓
              Jackie restarts gateway if config changed
                                ↓
                         Changes live ✅

Jackie edits config / writes notes
                                ↓
                  Writes to /data/vault/jackie/
                                ↓
          Commits + pushes on: conversation end / heartbeat
                                ↓
                GitHub updated → Obsidian auto-pulls
                                ↓
                    Lily sees changes in Obsidian ✅
```

---

## Implementation Plan

### Phase 1: Persistent Volume Migration + Vault as Source of Truth (P0)

Move all mutable files from Docker image to vault-backed `/data`.

#### Step 1.1: Create entrypoint.sh

```bash
#!/bin/bash
set -e

DATA_DIR="/data"
SKILLS_DIR="$DATA_DIR/skills"
VAULT_DIR="$DATA_DIR/vault"
WORKSPACE_DIR="$DATA_DIR/workspace"
PACKAGES_DIR="$DATA_DIR/packages"
VAULT_JACKIE="$VAULT_DIR/jackie"

# --- 1. Clone or pull vault ---
if [ -n "$GITHUB_TOKEN" ]; then
  git config --global user.name "Jackie"
  git config --global user.email "jackie@openclaw.ai"

  if [ ! -d "$VAULT_DIR/.git" ]; then
    echo "[entrypoint] Cloning vault..."
    git clone "https://${GITHUB_TOKEN}@github.com/lilyzhng/vault.git" "$VAULT_DIR"
  else
    echo "[entrypoint] Pulling latest vault..."
    cd "$VAULT_DIR" && git pull --rebase origin main || true
  fi
fi

# --- 2. Initialize workspace with symlinks to vault ---
mkdir -p "$WORKSPACE_DIR"
# Config files: vault is source of truth
[ -f "$VAULT_JACKIE/config/AGENTS.md" ] && ln -sf "$VAULT_JACKIE/config/AGENTS.md" "$WORKSPACE_DIR/AGENTS.md"
[ -f "$VAULT_JACKIE/config/HEARTBEAT.md" ] && ln -sf "$VAULT_JACKIE/config/HEARTBEAT.md" "$WORKSPACE_DIR/HEARTBEAT.md"
[ -f "$VAULT_JACKIE/config/SOUL.md" ] && ln -sf "$VAULT_JACKIE/config/SOUL.md" "$WORKSPACE_DIR/SOUL.md"
# Memory
[ -f "$VAULT_JACKIE/MEMORY.md" ] && ln -sf "$VAULT_JACKIE/MEMORY.md" "$WORKSPACE_DIR/MEMORY.md"

# --- 3. Initialize skills ---
# Copy factory defaults first (if skills dir doesn't exist)
if [ ! -d "$SKILLS_DIR" ]; then
  echo "[entrypoint] First run: copying default skills to persistent volume"
  cp -r /opt/sofagenius-skills-default "$SKILLS_DIR"
fi
# Then overlay any skills from vault (vault wins on conflict)
if [ -d "$VAULT_JACKIE/skills" ]; then
  cp -rn "$VAULT_JACKIE/skills/"* "$SKILLS_DIR/" 2>/dev/null || true
fi

# --- 4. Restore user-installed packages ---
mkdir -p "$PACKAGES_DIR"
if [ -f "$PACKAGES_DIR/apt-packages.txt" ]; then
  echo "[entrypoint] Restoring apt packages..."
  sudo apt-get update -qq
  xargs sudo apt-get install -y -qq < "$PACKAGES_DIR/apt-packages.txt" || true
fi
if [ -f "$PACKAGES_DIR/pip-packages.txt" ]; then
  echo "[entrypoint] Restoring pip packages..."
  xargs pip3 install --user -qq < "$PACKAGES_DIR/pip-packages.txt" || true
fi
if [ -f "$PACKAGES_DIR/npm-packages.txt" ]; then
  echo "[entrypoint] Restoring npm packages..."
  xargs sudo npm install -g < "$PACKAGES_DIR/npm-packages.txt" || true
fi

# --- 5. Start supervisor ---
echo "[entrypoint] Starting services..."
exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
```

#### Step 1.2: Update Dockerfile

Changes needed:

- Pre-install chromium + sudo
- Copy skills to `/opt/sofagenius-skills-default/` (factory defaults)
- Set entrypoint to `entrypoint.sh`

```dockerfile
# --- Pre-install chromium + sudo ---
RUN apt-get update && apt-get install -y \
    sudo \
    chromium \
    chromium-driver \
    && echo "node ALL=(ALL) NOPASSWD: /usr/bin/apt-get, /usr/bin/pip3, /usr/bin/pip, /usr/local/bin/npm, /usr/local/bin/npx, /usr/bin/supervisorctl, /usr/bin/chown" \
       > /etc/sudoers.d/node-limited \
    && chmod 440 /etc/sudoers.d/node-limited \
    && rm -rf /var/lib/apt/lists/*

# --- Copy defaults (used on first boot if vault doesn't have them yet) ---
COPY skills /opt/sofagenius-skills-default

# --- Entrypoint ---
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh
ENTRYPOINT ["/opt/entrypoint.sh"]
```

#### Step 1.3: Update openclaw.json

```jsonc
{
  "skills": {
    "load": {
      "extraDirs": ["/data/skills"], // was: /opt/sofagenius-skills
    },
  },
}
```

#### Step 1.4: Vault structure (create in lilyzhng/vault)

```
vault/jackie/
  config/
    AGENTS.md          ← moved from examples/sofagenius-flyio/AGENTS.md
    HEARTBEAT.md       ← moved from examples/sofagenius-flyio/HEARTBEAT.md
    SOUL.md            ← already exists as soul.md, rename/move
  skills/              ← backup of custom skills Jackie creates
  MEMORY.md            ← already exists
  *.md                 ← daily notes (already exists)
```

**Verification:**

- [ ] Deploy with new Dockerfile + entrypoint
- [ ] Confirm vault is cloned to `/data/vault` on boot
- [ ] Confirm `/data/workspace/AGENTS.md` is a symlink to vault
- [ ] Edit AGENTS.md in Obsidian → push → Jackie pulls on next heartbeat → change visible
- [ ] Jackie edits AGENTS.md → `supervisorctl restart` → change takes effect immediately
- [ ] Redeploy (new Docker image) — confirm `/data` contents survive

---

### Phase 2: Vault Bidirectional Sync (P0)

Hybrid sync: conversation start pull, conversation end push, heartbeat fallback.

#### Step 2.1: Add GITHUB_TOKEN as Fly secret

```bash
fly secrets set GITHUB_TOKEN=ghp_xxx -a openclaw-sofagenius
```

Use a fine-grained PAT scoped to `lilyzhng/vault` only (read+write contents).

#### Step 2.2: Sync triggers

| When                          | Action                              | How                                         |
| ----------------------------- | ----------------------------------- | ------------------------------------------- |
| Conversation start            | `git pull`                          | Add to AGENTS.md session-start instructions |
| Conversation end / compaction | `git add + commit + push`           | Update `openclaw.json` compaction prompt    |
| Every heartbeat (30min)       | `git pull` then `git push` if dirty | Add to HEARTBEAT.md                         |

#### Step 2.3: Update AGENTS.md session-start instructions

```markdown
## Session Start

1. Sync vault: `cd /data/vault && git pull --rebase origin main`
2. Read SOUL.md, USER.md, MEMORY.md from vault
3. Check for config changes Lily may have pushed
```

#### Step 2.4: Update openclaw.json compaction prompt

```
Pre-compaction memory flush. Save important conversation memories to the vault:
cd /data/vault && <write notes to jackie/YYYY-MM-DD-notes.md> &&
git add jackie/ && git commit -m "Jackie: memory flush" && git push
```

#### Step 2.5: Update HEARTBEAT.md vault sync section

```markdown
## Vault Sync (every heartbeat)

1. Pull latest: `cd /data/vault && git pull --rebase origin main`
2. If you wrote anything since last sync: `git add jackie/ && git commit -m "Jackie: heartbeat sync" && git push`
3. On conflict: keep both versions (append), never force-push
```

**Verification:**

- [ ] Jackie pulls vault on conversation start
- [ ] Jackie pushes notes on conversation end
- [ ] Heartbeat does pull+push every 30 min
- [ ] Lily's Obsidian edits appear in Jackie's next pull
- [ ] Phone Jackie and Discord Jackie see same MEMORY.md

---

### Phase 3: Self-Install Capability (P1)

Jackie can install system packages and persist them across restarts.

#### Step 3.1: Sudo whitelist (already in Phase 1 Dockerfile)

Whitelisted commands only — no `rm`, `chmod 777`, `curl | sh`, `bash`, or `kill -9`.

| Command         | Why Jackie needs it                                                                             |
| --------------- | ----------------------------------------------------------------------------------------------- |
| `apt-get`       | Install system packages (ffmpeg, imagemagick, etc.)                                             |
| `pip3`          | Install Python packages                                                                         |
| `npm` / `npx`   | Install Node tools (playwright, puppeteer, etc.)                                                |
| `supervisorctl` | Restart gateway or sofagenius after config changes — **enables live reload without VM restart** |
| `chown`         | Fix file permissions after package installs (apt sometimes breaks ownership)                    |

The key unlock is `supervisorctl` — Jackie can edit AGENTS.md then `sudo supervisorctl restart openclaw-gateway` to apply changes **in the current conversation**, not just next session.

#### Step 3.2: Install + record pattern

Add to AGENTS.md:

```markdown
## Installing New Tools

When you need a system package:

1. `sudo apt-get update && sudo apt-get install -y <package>`
2. Record it: `echo "<package>" >> /data/packages/apt-packages.txt`
3. The entrypoint script will auto-restore these on next boot.
4. Briefly tell Lily what you installed and why.

When you need a Python package:

1. `pip3 install --user <package>`
2. Record it: `echo "<package>" >> /data/packages/pip-packages.txt`

When you need a Node tool:

1. `sudo npm install -g <package>` or `npx <package>`
2. Record global installs: `echo "<package>" >> /data/packages/npm-packages.txt`

## Restarting Services (live reload)

After editing config files (AGENTS.md, HEARTBEAT.md, openclaw.json):

- `sudo supervisorctl restart openclaw-gateway` — apply changes immediately
- `sudo supervisorctl restart sofagenius-backend` — restart ML backend
- `sudo supervisorctl status` — check what's running
```

#### Step 3.3: Pre-installed packages (in Dockerfile)

Chromium is pre-installed. No boot-time recovery needed for it.

**Verification:**

- [ ] Jackie can install a package during conversation
- [ ] Package survives VM restart (via entrypoint recovery)
- [ ] Jackie cannot run arbitrary root commands (only whitelisted)
- [ ] Jackie notifies Lily after installing something

---

### Phase 4: Self-Modification (P1)

Jackie can update his own behavior, with minimal guardrails.

#### Step 4.1: Full autonomy on behavior files

Jackie can directly edit files in `/data/vault/jackie/config/`:

- `AGENTS.md` — behavior rules
- `HEARTBEAT.md` — proactive check config

Then `sudo supervisorctl restart openclaw-gateway` to apply immediately.

#### Step 4.2: Guardrails (minimal)

Add to AGENTS.md:

```markdown
## Self-Modification Rules

- You CAN freely edit AGENTS.md, HEARTBEAT.md, and any config to improve your behavior.
- You CAN restart services to apply changes immediately.
- You MUST commit changes to vault so Lily can see via git history.
- You SHOULD briefly mention what you changed in the current conversation.
- You MUST NOT delete safety rules (no data exfiltration, no unauthorized public posts).
- SOUL.md is your identity — you can evolve it, but be thoughtful about core personality changes.
- If you break yourself, Lily can restore from git history.
```

#### Step 4.3: Version tracking

Every self-modification committed to vault with a clear message:

```bash
cd /data/vault && git add jackie/ && \
  git commit -m "Jackie: updated AGENTS.md - added browser capability note" && \
  git push
```

**Verification:**

- [ ] Jackie can edit AGENTS.md and restart gateway
- [ ] Change appears in vault git history
- [ ] Lily sees the change in Obsidian
- [ ] Lily can revert any change via git

---

### Phase 5: Hot Skill Addition (P2)

Jackie can create new skills at runtime.

#### Step 5.1: Skill creation pattern

A skill is just a directory with `SKILL.md` + `scripts/`. Jackie can create one:

```bash
mkdir -p /data/skills/jackie-browser/scripts
# Write SKILL.md with tool definition
# Write script that uses chromium
```

#### Step 5.2: Skill discovery

Need to verify: does OpenClaw hot-reload skills from `extraDirs`, or only on session start?

- If session start only: new skills work on next conversation (or after `supervisorctl restart`)
- If hot-reload: new skills work immediately

**TODO:** Test OpenClaw skill loading behavior.

#### Step 5.3: Skill sharing via vault

Jackie commits new skills to vault so they're backed up and reviewable:

```
vault/jackie/skills/jackie-browser/SKILL.md
vault/jackie/skills/jackie-browser/scripts/browse.py
```

Entrypoint syncs vault skills to `/data/skills/` on boot.

**Verification:**

- [ ] Jackie can create a new skill directory
- [ ] Skill is usable (on next session or after restart)
- [ ] Skill is backed up to vault
- [ ] Skill appears in Lily's Obsidian vault

---

## Risk Mitigation

| Risk                               | Mitigation                                                                                                              |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **Prompt injection → root access** | Sudo whitelist: only `apt-get`, `pip3`, `npm`, `npx`, `supervisorctl`, `chown`. No `rm`, `chmod`, `curl \| sh`, `bash`. |
| **Jackie corrupts his own config** | Everything in vault with git history. `git revert` to restore any version.                                              |
| **Volume fills up**                | Monitor with heartbeat check. Expand volume via `fly volumes extend`. Currently at 5GB.                                 |
| **Git merge conflicts**            | Jackie uses append-only for daily notes. Conflicts: keep both versions, never force-push.                               |
| **Boot time creep**                | Graduate frequently-used packages from apt-packages.txt into Dockerfile. Review quarterly.                              |
| **Vault token leak**               | Fine-grained PAT scoped to single repo. Stored as Fly secret, not in code.                                              |

---

## Migration Checklist

- [ ] **Phase 1:** Create `entrypoint.sh`
- [ ] **Phase 1:** Update Dockerfile (chromium, sudo whitelist, entrypoint)
- [ ] **Phase 1:** Update `openclaw.json` (skills path, compaction prompt)
- [ ] **Phase 1:** Create `vault/jackie/config/` structure in GitHub vault
- [ ] **Phase 1:** Deploy and verify persistent volume + vault clone works
- [ ] **Phase 2:** Add GITHUB_TOKEN as Fly secret
- [ ] **Phase 2:** Update AGENTS.md with session-start vault pull
- [ ] **Phase 2:** Update HEARTBEAT.md with vault sync step
- [ ] **Phase 2:** Update compaction prompt for vault push
- [ ] **Phase 2:** Verify bidirectional sync (Obsidian ↔ Jackie)
- [ ] **Phase 3:** Verify sudo whitelist works, test package install + recovery
- [ ] **Phase 3:** Update AGENTS.md with install + restart instructions
- [ ] **Phase 4:** Update AGENTS.md with self-modification rules
- [ ] **Phase 4:** Test: Jackie edits config → restarts → change live
- [ ] **Phase 5:** Test skill hot-loading behavior
- [ ] **Phase 5:** Create skill-sharing-via-vault workflow

## Success Criteria

After all phases:

1. **Lily edits AGENTS.md in Obsidian** → push → Jackie auto-pulls → `supervisorctl restart` → live in seconds
2. **Jackie decides to change heartbeat frequency** → edits file → restarts → tells Lily "btw I changed heartbeat to 15min" → done
3. **Jackie needs a new tool** → `sudo apt-get install` → records → notifies → available immediately
4. **Jackie has a phone call** → Discord Jackie remembers it (same vault)
5. **Lily reviews Jackie's self-modifications** → opens Obsidian → sees git history
6. **Docker rebuild only needed for** Node/Python version upgrades or core OpenClaw updates
