#!/bin/bash
set -e

DATA_DIR="/data"
SKILLS_DIR="$DATA_DIR/skills"
VAULT_DIR="$DATA_DIR/vault"
WORKSPACE_DIR="$DATA_DIR/workspace"
PACKAGES_DIR="$DATA_DIR/packages"
VAULT_JACKIE="$VAULT_DIR/jackie"

echo "[entrypoint] Starting Jackie VM setup..."

# --- 0. Fix ownership (volume mount resets ownership) ---
chown -R node:node "$DATA_DIR"
chmod 1777 /tmp

# From here on, run as node user logic but we stay root for package restore
# We'll drop to node via supervisor for the actual services

# --- 1. Clone or pull vault (source of truth for config + memory) ---
# Accept either GH_TOKEN or GITHUB_TOKEN
VAULT_TOKEN="${GH_TOKEN:-$GITHUB_TOKEN}"

if [ -n "$VAULT_TOKEN" ]; then
  # Configure git as node user
  su node -c 'git config --global user.name "Jackie"'
  su node -c 'git config --global user.email "jackie@openclaw.ai"'
  su node -c 'git config --global pull.rebase true'

  if [ ! -d "$VAULT_DIR/.git" ]; then
    echo "[entrypoint] Cloning vault..."
    su node -c "git clone 'https://${VAULT_TOKEN}@github.com/lilyzhng/vault.git' '$VAULT_DIR'"
  else
    echo "[entrypoint] Pulling latest vault..."
    su node -c "cd '$VAULT_DIR' && git pull --rebase origin main" || true
  fi
else
  echo "[entrypoint] WARNING: GH_TOKEN/GITHUB_TOKEN not set, skipping vault sync"
fi

# --- 2. Initialize workspace with symlinks to vault ---
mkdir -p "$WORKSPACE_DIR"
chown node:node "$WORKSPACE_DIR"

# Config files: vault is source of truth (symlink if they exist)
if [ -d "$VAULT_JACKIE/config" ]; then
  [ -f "$VAULT_JACKIE/config/AGENTS.md" ] && ln -sf "$VAULT_JACKIE/config/AGENTS.md" "$WORKSPACE_DIR/AGENTS.md"
  [ -f "$VAULT_JACKIE/config/HEARTBEAT.md" ] && ln -sf "$VAULT_JACKIE/config/HEARTBEAT.md" "$WORKSPACE_DIR/HEARTBEAT.md"
  [ -f "$VAULT_JACKIE/config/SOUL.md" ] && ln -sf "$VAULT_JACKIE/config/SOUL.md" "$WORKSPACE_DIR/SOUL.md"
  echo "[entrypoint] Linked vault config → workspace"
else
  # Fallback: copy factory defaults if vault doesn't have config yet
  echo "[entrypoint] Vault config not found, using factory defaults"
  [ -f /opt/defaults/AGENTS.md ] && [ ! -f "$WORKSPACE_DIR/AGENTS.md" ] && \
    cp /opt/defaults/AGENTS.md "$WORKSPACE_DIR/"
  [ -f /opt/defaults/HEARTBEAT.md ] && [ ! -f "$WORKSPACE_DIR/HEARTBEAT.md" ] && \
    cp /opt/defaults/HEARTBEAT.md "$WORKSPACE_DIR/"
fi

# Link openclaw.json so gateway finds it from /data/workspace
ln -sf /app/openclaw.json "$WORKSPACE_DIR/openclaw.json"

# Memory symlinks (new tiered structure)
[ -f "$VAULT_JACKIE/memory/long-term.md" ] && ln -sf "$VAULT_JACKIE/memory/long-term.md" "$WORKSPACE_DIR/MEMORY.md"
[ -d "$VAULT_JACKIE/memory" ] && ln -sf "$VAULT_JACKIE/memory" "$WORKSPACE_DIR/memory"

# Initialize .learnings/ if it doesn't exist in vault
if [ -d "$VAULT_DIR/.git" ] && [ ! -d "$VAULT_JACKIE/.learnings" ]; then
  echo "[entrypoint] Initializing .learnings/ in vault..."
  mkdir -p "$VAULT_JACKIE/.learnings"
  [ -d /opt/vault-init/jackie/.learnings ] && cp /opt/vault-init/jackie/.learnings/*.md "$VAULT_JACKIE/.learnings/"
  chown -R node:node "$VAULT_JACKIE/.learnings"
  su node -c "cd '$VAULT_DIR' && git add jackie/.learnings/ && git commit -m 'Jackie: initialize self-improvement learnings' && git push" || true
fi

# --- 3. Initialize skills ---
if [ ! -d "$SKILLS_DIR" ]; then
  echo "[entrypoint] First run: copying default skills to persistent volume"
  cp -r /opt/sofagenius-skills-default "$SKILLS_DIR"
  chown -R node:node "$SKILLS_DIR"
fi

# Overlay any skills from vault (vault wins on conflict)
if [ -d "$VAULT_JACKIE/skills" ]; then
  cp -rn "$VAULT_JACKIE/skills/"* "$SKILLS_DIR/" 2>/dev/null || true
  chown -R node:node "$SKILLS_DIR"
  echo "[entrypoint] Synced vault skills → /data/skills"
fi

# --- 4. Restore user-installed packages ---
mkdir -p "$PACKAGES_DIR"
chown node:node "$PACKAGES_DIR"

if [ -f "$PACKAGES_DIR/apt-packages.txt" ] && [ -s "$PACKAGES_DIR/apt-packages.txt" ]; then
  echo "[entrypoint] Restoring apt packages..."
  apt-get update -qq
  xargs apt-get install -y -qq < "$PACKAGES_DIR/apt-packages.txt" || true
  rm -rf /var/lib/apt/lists/*
fi

if [ -f "$PACKAGES_DIR/pip-packages.txt" ] && [ -s "$PACKAGES_DIR/pip-packages.txt" ]; then
  echo "[entrypoint] Restoring pip packages..."
  su node -c "xargs pip3 install --user --break-system-packages -qq < '$PACKAGES_DIR/pip-packages.txt'" || true
fi

if [ -f "$PACKAGES_DIR/npm-packages.txt" ] && [ -s "$PACKAGES_DIR/npm-packages.txt" ]; then
  echo "[entrypoint] Restoring npm packages..."
  xargs npm install -g < "$PACKAGES_DIR/npm-packages.txt" || true
fi

# --- 5. Start supervisor ---
echo "[entrypoint] Setup complete. Starting services..."
exec supervisord -n -c /etc/supervisor/conf.d/openclaw-sofagenius.conf
