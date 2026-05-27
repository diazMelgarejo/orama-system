#!/usr/bin/env bash
# Cursor Cloud VM install — idempotent sibling-repo bootstrap + venv.
# Invoked from .cursor/environment.json "install".
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

HOME="${HOME:-/home/ubuntu}"
case "${OPENCLAW_HOME:-}" in
  "" | "/" | '/openclaw-v1' | '$HOME/openclaw-v1')
    export OPENCLAW_HOME="$HOME/openclaw-v1"
    ;;
esac
export OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw-v1}"

log() { printf '>>> [cloud-install] %s\n' "$*"; }

venv_healthy() {
  [[ -f .venv/bin/activate ]] && [[ -x .venv/bin/python ]] && .venv/bin/python -m pip --version >/dev/null 2>&1
}

ensure_python_venv_package() {
  if python3 -c 'import ensurepip' >/dev/null 2>&1; then
    return 0
  fi
  log "ensurepip missing; installing python3-venv via apt"
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "cloud-install: apt-get not found; cannot install python3-venv" >&2
    return 1
  fi
  sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv python3.12-venv
}

ensure_venv() {
  ensure_python_venv_package
  if [[ -d .venv ]] && ! venv_healthy; then
    log "removing broken .venv"
    rm -rf .venv
  fi
  if ! venv_healthy; then
    log "creating .venv"
    python3 -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install -q --upgrade pip
}

clone_sibling() {
  local name="$1"
  local url="$2"
  local branch="${3:-main}"
  local dest="$OPENCLAW_HOME/$name"
  if [[ -d "$dest/.git" ]]; then
    log "$name already present at $dest"
    return 0
  fi
  log "cloning $name (branch $branch) -> $dest"
  mkdir -p "$OPENCLAW_HOME"
  git clone --branch "$branch" --depth 1 "$url" "$dest"
}

clone_alphaclaw_fork() {
  local url="https://github.com/diazMelgarejo/AlphaClaw"
  local dest="$OPENCLAW_HOME/AlphaClaw"
  local upstream="${ALPHACLAW_UPSTREAM_BRANCH:-main}"
  if [[ -d "$dest/.git" ]]; then
    log "AlphaClaw present; align integration + contrib branches"
    bash "$REPO_ROOT/scripts/git/alphaclaw-align-all.sh"
    return 0
  fi
  log "cloning AlphaClaw (upstream $upstream) -> $dest"
  mkdir -p "$OPENCLAW_HOME"
  git clone --branch "$upstream" --depth 1 "$url" "$dest"
  bash "$REPO_ROOT/scripts/git/alphaclaw-align-all.sh"
}

log "OPENCLAW_HOME=$OPENCLAW_HOME"
ensure_venv

clone_sibling Perpetua-Tools https://github.com/diazMelgarejo/Perpetua-Tools
clone_alphaclaw_fork

log "pip install orama-system + siblings"
pip install -q -e ".[test]"
pip install -q -e "$OPENCLAW_HOME/Perpetua-Tools"
pip install -q pytest pytest-asyncio pyyaml

if [[ -f "$OPENCLAW_HOME/AlphaClaw/package.json" ]]; then
  log "npm install AlphaClaw"
  (cd "$OPENCLAW_HOME/AlphaClaw" && npm install)
fi

if ! npm list -g openclaw >/dev/null 2>&1; then
  log "npm install -g openclaw@2026.5.6"
  npm install -g openclaw@2026.5.6
fi

if [[ -x scripts/cursor/install-user-git-environment.sh ]]; then
  log "install user-level git guards (~/.cursor/openclaw)"
  bash scripts/cursor/install-user-git-environment.sh
elif [[ -x scripts/git/apply-attribution-guard-all-repos.sh ]]; then
  log "apply git attribution guards"
  bash scripts/git/apply-attribution-guard-all-repos.sh
fi

log "complete"
