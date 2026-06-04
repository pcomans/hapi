#!/bin/bash
# SessionStart hook — provisions the multi-substrate CIDOC-CRM authority POC environment.
#
# Stands up the four ADR-018 substrate adapters' backing services:
#   1. Postgres 16            — relational-E13 adapter (and AGE host)         [REQUIRED]
#   2. Apache AGE in Postgres — Cypher-in-Postgres adapter                    [BEST-EFFORT: skipped on build failure]
#   3. Neo4j Community        — graph-native adapter                          [REQUIRED if download works]
#   4. rdflib (via uv)        — strict-CIDOC-RDF adapter + RDFS/OWL reasoning [REQUIRED]
#
# Idempotent: every step is skip-if-already-present, so re-running on each
# session start is cheap once the container cache is warm. The expensive
# one-time work (AGE compile, Neo4j download) only runs on a cold container.
#
# AGE is best-effort by design (per maintainer instruction): if flex / the
# server-dev headers / the compile fail, AGE is skipped and the POC proceeds
# on the other three adapters. Nothing here aborts the session on AGE failure.
set -uo pipefail

# Only provision in the remote (Claude Code on the web) container. Locally this
# is a no-op so a developer's machine isn't mutated with apt/Neo4j installs.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Async: the cold-container path (AGE compile + Neo4j download) takes minutes;
# run it in the background so session startup isn't blocked. On a warm container
# every step is skip-if-present, so the async work finishes near-instantly.
echo '{"async": true, "asyncTimeout": 600000}'

log() { echo "[session-start] $*"; }

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
NEO4J_HOME="/opt/neo4j"
NEO4J_VERSION="5.26.0"
AGE_SRC="/opt/age-src"
PG_CONFIG="/usr/lib/postgresql/16/bin/pg_config"

# ---------------------------------------------------------------------------
# 1. System packages (idempotent — apt/dpkg no-op when already installed)
# ---------------------------------------------------------------------------
export DEBIAN_FRONTEND=noninteractive
missing_pkgs=()
for pkg in flex postgresql-server-dev-16; do
  dpkg -s "$pkg" >/dev/null 2>&1 || missing_pkgs+=("$pkg")
done
if [ "${#missing_pkgs[@]}" -gt 0 ]; then
  log "installing system packages: ${missing_pkgs[*]}"
  apt-get update -qq  && apt-get install -y -qq "${missing_pkgs[@]}" \
    || log "WARN: apt install failed (AGE build may be skipped)"
fi

# ---------------------------------------------------------------------------
# 2. Postgres cluster up + POC role/database
# ---------------------------------------------------------------------------
if ! pg_isready -q 2>/dev/null; then
  log "starting Postgres 16 cluster"
  pg_ctlcluster 16 main start || log "WARN: postgres start failed"
fi

if pg_isready -q 2>/dev/null; then
  sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='hapi'" 2>/dev/null | grep -q 1 \
    || sudo -u postgres psql -qc "CREATE ROLE hapi LOGIN SUPERUSER PASSWORD 'hapi';" \
    && log "ensured role 'hapi'"
  sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='hapi_poc'" 2>/dev/null | grep -q 1 \
    || sudo -u postgres psql -qc "CREATE DATABASE hapi_poc OWNER hapi;" \
    && log "ensured database 'hapi_poc'"
fi

# ---------------------------------------------------------------------------
# 3. Apache AGE — BEST-EFFORT. Skipped silently (warning only) on any failure.
# ---------------------------------------------------------------------------
age_present() {
  sudo -u postgres psql -d hapi_poc -tAc \
    "SELECT 1 FROM pg_available_extensions WHERE name='age'" 2>/dev/null | grep -q 1
}
if age_present; then
  log "Apache AGE already available — skipping build"
elif [ ! -x "$PG_CONFIG" ] || ! command -v flex >/dev/null 2>&1; then
  log "AGE prerequisites missing (pg_config/flex) — skipping AGE (per best-effort policy)"
else
  log "building Apache AGE (best-effort)..."
  (
    set -e
    if [ ! -d "$AGE_SRC" ]; then
      # master tracks current PG majors (incl. PG16); shallow clone keeps it fast.
      git clone --depth 1 https://github.com/apache/age.git "$AGE_SRC"
    fi
    cd "$AGE_SRC"
    make PG_CONFIG="$PG_CONFIG"
    make PG_CONFIG="$PG_CONFIG" install
  ) && log "AGE build succeeded" \
    || log "WARN: AGE build failed — skipping AGE; POC proceeds on the other three adapters"
fi

# ---------------------------------------------------------------------------
# 4. Neo4j Community (Java 21 already present in the base image)
# ---------------------------------------------------------------------------
if [ ! -x "$NEO4J_HOME/bin/neo4j" ]; then
  log "downloading Neo4j Community ${NEO4J_VERSION}"
  if curl -fsSL "https://dist.neo4j.org/neo4j-community-${NEO4J_VERSION}-unix.tar.gz" -o /tmp/neo4j.tgz; then
    mkdir -p "$NEO4J_HOME"
    tar -xzf /tmp/neo4j.tgz -C "$NEO4J_HOME" --strip-components=1 && log "Neo4j extracted to $NEO4J_HOME"
    rm -f /tmp/neo4j.tgz
  else
    log "WARN: Neo4j download failed"
  fi
fi
if [ -x "$NEO4J_HOME/bin/neo4j" ]; then
  # Set the initial password (no-op / harmless error once the store exists).
  "$NEO4J_HOME/bin/neo4j-admin" dbms set-initial-password "${HAPI_NEO4J_PASSWORD:-hapi_poc_pw}" >/dev/null 2>&1 || true
  if ! "$NEO4J_HOME/bin/neo4j" status >/dev/null 2>&1; then
    log "starting Neo4j"
    "$NEO4J_HOME/bin/neo4j" start >/dev/null 2>&1 || log "WARN: neo4j start failed"
  fi
fi

# ---------------------------------------------------------------------------
# 5. Python deps (rdflib, neo4j driver, anthropic) via uv — declared in
#    pipeline/pyproject.toml so this is the single source of truth.
# ---------------------------------------------------------------------------
if [ -f "$PROJECT_DIR/pipeline/pyproject.toml" ]; then
  log "syncing pipeline Python deps (uv sync)"
  ( cd "$PROJECT_DIR/pipeline" && uv sync ) || log "WARN: uv sync failed"
fi

# ---------------------------------------------------------------------------
# 6. Persist connection info for the session
# ---------------------------------------------------------------------------
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export HAPI_PG_DSN='postgresql+psycopg2://hapi:hapi@127.0.0.1:5432/hapi_poc'"
    echo "export HAPI_NEO4J_URI='bolt://127.0.0.1:7687'"
    echo "export HAPI_NEO4J_USER='neo4j'"
    echo "export HAPI_NEO4J_PASSWORD='hapi_poc_pw'"
    echo "export NEO4J_HOME='$NEO4J_HOME'"
  } >> "$CLAUDE_ENV_FILE"
fi

log "provisioning complete"
