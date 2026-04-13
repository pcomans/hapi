#!/usr/bin/env bash
set -euo pipefail

# Launch a Docker AI Sandbox for Hapi development.
#
# The sandbox is an isolated container with its own Docker daemon,
# filesystem, and network. Claude Code runs inside with full permissions
# (--dangerously-skip-permissions) — safe because nothing on your host
# is at risk. The repo is cloned fresh from GitHub inside the sandbox.
#
# Prerequisites:
#   - Docker Desktop with the sbx plugin (https://docs.docker.com/ai/sandboxes/)
#   - gh CLI authenticated (https://cli.github.com/)
#   - Claude Max subscription (no API key needed)
#
# Usage:
#   ./scripts/sandbox.sh              # launch sandbox named "hapi"
#   ./scripts/sandbox.sh my-sandbox   # launch with a custom name
#   SBX_SKIP_SECRET=1 ./scripts/sandbox.sh  # skip GitHub secret setup

SANDBOX_NAME="${1:-hapi}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[x]${NC} $*" >&2; exit 1; }

# --- Pre-flight checks ---

command -v sbx  >/dev/null 2>&1 || error "sbx CLI not found. Install Docker Desktop: https://docs.docker.com/ai/sandboxes/"
command -v gh   >/dev/null 2>&1 || error "gh CLI not found. Install: https://cli.github.com/"
gh auth status  >/dev/null 2>&1 || error "gh CLI not authenticated. Run: gh auth login"

# --- GitHub secret ---

if [[ "${SBX_SKIP_SECRET:-}" != "1" ]]; then
    info "Setting GitHub token for sandbox access to private repo..."
    sbx secret set -g github -t "$(gh auth token)"
fi

# --- Check if sandbox already exists ---

if sbx ls 2>/dev/null | grep -q "$SANDBOX_NAME"; then
    warn "Sandbox '$SANDBOX_NAME' already exists."
    echo ""
    echo "  Resume:   sbx start $SANDBOX_NAME && sbx attach $SANDBOX_NAME"
    echo "  Shell:    sbx exec -it $SANDBOX_NAME bash"
    echo "  Destroy:  sbx rm $SANDBOX_NAME"
    echo ""
    read -rp "Start and attach to existing sandbox? [Y/n] " choice
    case "${choice:-Y}" in
        [Yy]*|"")
            sbx start "$SANDBOX_NAME" 2>/dev/null || true
            exec sbx attach "$SANDBOX_NAME"
            ;;
        *)
            exit 0
            ;;
    esac
fi

# --- Launch ---

info "Creating sandbox '$SANDBOX_NAME'..."
info "You'll authenticate via browser (Claude Max subscription)."
echo ""

sbx run --name "$SANDBOX_NAME" claude

# The sandbox is now running and attached. When you detach or exit,
# the script continues here.

echo ""
info "Sandbox '$SANDBOX_NAME' is running."
echo ""
echo "  Attach:   sbx attach $SANDBOX_NAME"
echo "  Shell:    sbx exec -it $SANDBOX_NAME bash"
echo "  Ports:    sbx ports $SANDBOX_NAME --publish 3000:3000"
echo "  Stop:     sbx stop $SANDBOX_NAME"
echo "  Destroy:  sbx rm $SANDBOX_NAME"
