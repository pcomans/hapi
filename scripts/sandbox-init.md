# Sandbox Init Prompt

Paste this as your first prompt after launching the sandbox.

---

Clone the repo and set up the dev environment. You have unrestricted
network access. No sudo — install tools in userspace.

1. git clone https://github.com/pcomans/hapi.git && cd hapi
2. docker compose up -d
3. cd pipeline && uv sync && cd ..
4. cd web && npm install -g pnpm && pnpm install && cd ..
5. cd pipeline && uv run alembic upgrade head && cd ..
6. cd pipeline && uv run pytest
7. cd web && pnpm typecheck

If a step fails, diagnose and fix before continuing. If `npm install -g`
fails due to permissions, use `corepack enable --install-directory=$HOME/.local/bin`
or `curl -fsSL https://get.pnpm.io/install.sh | sh` instead.

If everything passes, say "Ready." Then read docs/mvp-tasks.md and
await further instructions.
