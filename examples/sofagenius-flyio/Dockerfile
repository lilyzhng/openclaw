# OpenClaw + SofaGenius API Bridge Dockerfile
# Runs both OpenClaw gateway and SofaGenius FastAPI backend on the same container.
#
# SofaGenius stays intact as its own project — OpenClaw talks to it via HTTP.
# Update SofaGenius independently; OpenClaw skills just forward API calls.

FROM node:22-bookworm

# -- System deps + sudo + chromium --
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv git curl ca-certificates supervisor \
      sudo chromium poppler-utils \
    && echo "node ALL=(ALL) NOPASSWD: /usr/bin/apt-get, /usr/bin/pip3, /usr/bin/pip, /usr/local/bin/npm, /usr/local/bin/npx, /usr/bin/supervisorctl, /usr/bin/chown" \
       > /etc/sudoers.d/node-limited \
    && chmod 440 /etc/sudoers.d/node-limited \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# -- Python ML packages (SofaGenius deps) --
RUN python3 -m pip install --break-system-packages \
      fastapi uvicorn httpx pydantic \
      anthropic \
      wandb \
      huggingface_hub datasets \
      modal \
      duckdb \
      Pillow \
      supabase python-jose[cryptography] \
      tweepy numpy \
      google-auth

# -- Install ngrok (required for voice-call webhook tunnel) --
RUN curl -fsSL https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz \
    | tar xz -C /usr/local/bin

# -- Install Bun (required for OpenClaw build) --
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:${PATH}"

RUN corepack enable

# -- OpenClaw build --
WORKDIR /app
RUN chown node:node /app

COPY --chown=node:node package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY --chown=node:node ui/package.json ./ui/package.json
COPY --chown=node:node patches ./patches
COPY --chown=node:node scripts ./scripts

USER node
RUN NODE_OPTIONS=--max-old-space-size=2048 pnpm install --frozen-lockfile

USER root
USER node
COPY --chown=node:node . .
RUN for dir in /app/extensions /app/.agent /app/.agents; do \
      if [ -d "$dir" ]; then \
        find "$dir" -type d -exec chmod 755 {} +; \
        find "$dir" -type f -exec chmod 644 {} +; \
      fi; \
    done
RUN pnpm build
ENV OPENCLAW_PREFER_PNPM=1
RUN pnpm ui:build

USER root
RUN ln -sf /app/openclaw.mjs /usr/local/bin/openclaw \
 && chmod 755 /app/openclaw.mjs

# -- SofaGenius clone (pulled at build time, update with rebuild) --
RUN git clone https://github.com/lilyzhng/SofaGenius.git /opt/sofagenius \
 && cd /opt/sofagenius/backend \
 && python3 -m pip install --break-system-packages -r requirements.txt 2>/dev/null || true

# -- Mount bridge router into SofaGenius (exposes subagent tools as REST endpoints) --
RUN python3 /app/examples/sofagenius-flyio/mount_bridge.py

RUN chown -R node:node /opt/sofagenius

# -- Skills factory defaults (copied to /data/skills on first boot) --
COPY examples/sofagenius-flyio/skills /opt/sofagenius-skills-default
RUN chown -R node:node /opt/sofagenius-skills-default

# -- Config factory defaults (used if vault doesn't have config yet) --
RUN mkdir -p /opt/defaults
COPY examples/sofagenius-flyio/AGENTS.md /opt/defaults/AGENTS.md
COPY examples/sofagenius-flyio/HEARTBEAT.md /opt/defaults/HEARTBEAT.md

# -- Vault init templates (used on first boot to seed vault structure) --
COPY examples/sofagenius-flyio/vault-init /opt/vault-init

# -- Exec approvals (auto-approve python3 skill scripts without manual gates) --
RUN mkdir -p /home/node/.openclaw /home/node/.openclaw/workspace
COPY examples/sofagenius-flyio/exec-approvals.json /home/node/.openclaw/exec-approvals.json
RUN chown -R node:node /home/node/.openclaw

# -- OpenClaw config (gateway settings, allowed origins, skills) --
COPY examples/sofagenius-flyio/openclaw.json /app/openclaw.json

# -- Supervisor config (runs both services) --
COPY examples/sofagenius-flyio/supervisord.conf /etc/supervisor/conf.d/openclaw-sofagenius.conf

# -- Entrypoint (vault sync, skills init, package restore, then supervisor) --
COPY examples/sofagenius-flyio/entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

ENV NODE_ENV=production

# Expose OpenClaw gateway (3000) and SofaGenius API (8000)
EXPOSE 3000 8000

ENTRYPOINT ["/opt/entrypoint.sh"]
