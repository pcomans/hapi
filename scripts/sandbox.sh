#!/usr/bin/env bash
set -euo pipefail

# Launch a Docker AI Sandbox for Hapi development.
#
# The sandbox is a fully isolated container — its own filesystem, Docker
# daemon, and network. Claude Code runs with full permissions and Agent
# Teams enabled. Nothing on the host is mounted or exposed.
#
# The repo is cloned from GitHub inside the sandbox, not mounted from
# the host. When you `sbx rm`, everything is gone.
#
# Prerequisites:
#   - Docker Desktop with the sbx plugin (https://docs.docker.com/ai/sandboxes/)
#   - gh CLI authenticated (https://cli.github.com/)
#   - Claude Max subscription (no API key needed)
#   - sbx network policy set to Open (`sbx login` → choose Open)
#
# Usage:
#   ./scripts/sandbox.sh              # launch sandbox named "hapi"
#   ./scripts/sandbox.sh my-sandbox   # launch with a custom name

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

info "Setting GitHub token for sandbox access to private repo..."
sbx secret set -g github -t "$(gh auth token)"

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

# --- Launch from an empty temp dir so nothing on the host is mounted ---

WORKSPACE=$(mktemp -d)
trap 'rmdir "$WORKSPACE" 2>/dev/null || true' EXIT

info "Creating sandbox '$SANDBOX_NAME' (no host mount)..."
info "Authenticate via browser when prompted (Claude Max subscription)."
echo ""

(cd "$WORKSPACE" && sbx run --name "$SANDBOX_NAME" claude)

echo ""
info "Sandbox '$SANDBOX_NAME' is running."
echo ""
echo "  Attach:   sbx attach $SANDBOX_NAME"
echo "  Shell:    sbx exec -it $SANDBOX_NAME bash"
echo "  Ports:    sbx ports $SANDBOX_NAME --publish 3000:3000"
echo "  Stop:     sbx stop $SANDBOX_NAME"
echo "  Destroy:  sbx rm $SANDBOX_NAME"
