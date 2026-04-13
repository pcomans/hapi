# Sandbox Init Prompt

Paste this as your first prompt after launching the sandbox.

---

Install tools, clone the repo, and set up the dev environment:

1. sudo apt-get update && sudo apt-get install -y tmux
2. curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.bashrc
3. git clone https://github.com/pcomans/hapi.git && cd hapi
4. docker compose up -d
5. cd pipeline && uv sync && cd ..
6. cd web && pnpm install && cd ..
7. cd pipeline && uv run alembic upgrade head && cd ..
8. cd pipeline && uv run pytest
9. cd web && pnpm typecheck

Report status of each step. If everything passes, say "Ready."
