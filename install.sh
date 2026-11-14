#!/usr/bin/env bash
# install.sh
# The ὅραμα System — Single-Agent + ECC/Codex Harness Installer
# =================================================================
# Installs the ultrathink skill to ~/.claude/skills/orama-system/
# Works with Claude Code CLI, Codex/OpenCode, and ECC.
#
# Usage:
#   curl -sL https://raw.githubusercontent.com/diazMelgarejo/orama-system/main/install.sh | bash
#   # or locally:
#   bash install.sh
#   bash install.sh --project     # install to ./.claude/skills/ instead of global
#   bash install.sh --with-test-deps  # also install Python deps for pytest/PoCs
#   bash install.sh --with-agent-scripts  # also bootstrap steipete/agent-scripts (opt-in)
#   bash install.sh --uninstall   # remove the skill

set -euo pipefail

# ─── Config ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; RED='\033[0;31m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "  ${GREEN}✓${RESET} $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}  $1"; }
info() { echo -e "  ${BLUE}→${RESET} $1"; }

SKILL_NAME="orama-system"
REPO_URL="https://github.com/diazMelgarejo/orama-system"
BRANCH="main"
SKILL_SOURCE="bin/orama-system"

# steipete/agent-scripts bootstrap (opt-in, Phase 4)
STEIPETE_REPO="https://github.com/steipete/agent-scripts"
AGENT_SCRIPTS_DIR="$HOME/Projects/agent-scripts"
AGENT_SCRIPTS_LINK="$HOME/.agent-scripts"
WITH_AGENT_SCRIPTS=0

# Default: global install
INSTALL_DIR="$HOME/.claude/skills/$SKILL_NAME"
MODE="global"
WITH_TEST_DEPS=0

# ─── Argument parsing ────────────────────────────────────────────────────────
for arg in "$@"; do
  case $arg in
    --project|-p)
      INSTALL_DIR="./.claude/skills/$SKILL_NAME"
      MODE="project"
      ;;
    --uninstall|-u)
      echo -e "${YELLOW}Removing ultrathink skill...${RESET}"
      rm -rf "$HOME/.claude/skills/$SKILL_NAME" 2>/dev/null
      rm -rf "./.claude/skills/$SKILL_NAME" 2>/dev/null
      rm -rf "$HOME/.ecc/skills/$SKILL_NAME" 2>/dev/null
      rm -rf "./.ecc/skills/$SKILL_NAME" 2>/dev/null
      echo -e "${GREEN}Done.${RESET}"
      exit 0
      ;;
    --with-test-deps)
      WITH_TEST_DEPS=1
      ;;
    --with-agent-scripts)
      WITH_AGENT_SCRIPTS=1
      ;;
    --help|-h)
      echo "Usage: install.sh [--project] [--with-test-deps] [--uninstall]"
      echo "  --project   Install to ./.claude/skills/ (project-local)"
      echo "  --with-test-deps  Install runtime/test deps for pytest and FastAPI PoCs"
      echo "  --uninstall Remove the ultrathink skill"
      exit 0
      ;;
  esac
done

# ─── Detect source ───────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo ". ")"
LOCAL_SOURCE="$SCRIPT_DIR/$SKILL_SOURCE"
TMPDIR=""

echo ""
echo -e "${BOLD}🚀 The ὅραμα System — Harness Install${RESET}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  Mode:    ${BLUE}$MODE${RESET}"
echo -e "  Target:  ${BLUE}$INSTALL_DIR${RESET}"
echo ""

# ─── Install Core Skill ──────────────────────────────────────────────────────
if [[ -d "$LOCAL_SOURCE" ]]; then
  # Local install — copy from adjacent single_agent/ directory
  echo -e "  ${GREEN}Found local source:${RESET} $LOCAL_SOURCE"
  mkdir -p "$(dirname "$INSTALL_DIR")"
  rm -rf "$INSTALL_DIR"
  cp -R "$LOCAL_SOURCE" "$INSTALL_DIR"
else
  # Remote install — clone from GitHub
  echo -e "  ${BLUE}Fetching from GitHub...${RESET}"
  TMPDIR=$(mktemp -d)
  trap "rm -rf $TMPDIR" EXIT

  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMPDIR/repo" 2>/dev/null

  if [[ ! -d "$TMPDIR/repo/$SKILL_SOURCE" ]]; then
    echo -e "  ${RED}Error: $SKILL_SOURCE not found in repo${RESET}"
    exit 1
  fi

  mkdir -p "$(dirname "$INSTALL_DIR")"
  rm -rf "$INSTALL_DIR"
  cp -R "$TMPDIR/repo/$SKILL_SOURCE" "$INSTALL_DIR"
  LOCAL_SOURCE="$TMPDIR/repo/$SKILL_SOURCE"
fi

# ─── Make scripts executable ─────────────────────────────────────────────────
chmod +x "$INSTALL_DIR/scripts/"*.py "$INSTALL_DIR/scripts/"*.sh 2>/dev/null || true

# ─── Optional Python test dependency bootstrap ────────────────────────────────
if [[ "$WITH_TEST_DEPS" == "1" ]]; then
  if [[ -f "$SCRIPT_DIR/scripts/install-test-deps.sh" ]]; then
    info "Installing Python runtime/test dependencies for pytest and FastAPI PoCs..."
    bash "$SCRIPT_DIR/scripts/install-test-deps.sh"
  else
    warn "scripts/install-test-deps.sh not found — skip Python dependency install"
  fi
fi

# ─── ECC Harness Hook ────────────────────────────────────────────────────────
for ECC_CANDIDATE in "$SCRIPT_DIR/.ecc" "$HOME/.ecc" ".ecc"; do
  if [ -d "$ECC_CANDIDATE" ]; then
    ECC_SKILLS="$ECC_CANDIDATE/skills/$SKILL_NAME"
    mkdir -p "$ECC_SKILLS"
    cp    "$LOCAL_SOURCE/SKILL.md"   "$ECC_SKILLS/"
    cp -r "$LOCAL_SOURCE/cidf"       "$ECC_SKILLS/" 2>/dev/null || true
    cp -r "$LOCAL_SOURCE/references" "$ECC_SKILLS/" 2>/dev/null || true
    ok ".ecc/skills/$SKILL_NAME/             (ECC harness)"
    break
  fi
done
if [ ! -d "${SCRIPT_DIR}/.ecc" ] && [ ! -d "$HOME/.ecc" ] && [ ! -d ".ecc" ]; then
  warn ".ecc/ not found — skip ECC install. Run after:"
  echo "        git clone https://github.com/affaan-m/everything-claude-code .ecc"
fi

# ─── Task Template Bootstrap ──────────────────────────────────────────────────
mkdir -p "$HOME/.ultrathink/tasks"
cp "$LOCAL_SOURCE/templates/"* "$HOME/.ultrathink/tasks/" 2>/dev/null || true
ok "~/.ultrathink/tasks/                             (plan + lessons templates)"

# ─── Local mesh continuity (before IP expunge from tracked config) ───────────
MESH_DIR="$SCRIPT_DIR/scripts/mesh"
if [[ -f "$MESH_DIR/lan_topology_archive.py" ]]; then
  python3 "$MESH_DIR/lan_topology_archive.py" --ensure-local-cache \
    || warn "LAN topology archive step failed — run: python3 scripts/mesh/lan_topology_archive.py --backup --ref origin/main"
fi
if [[ -f "$MESH_DIR/ensure_local_mesh_secrets.py" ]]; then
  python3 "$MESH_DIR/ensure_local_mesh_secrets.py" \
    || warn "GOSSIP_SHARED_SECRET not written — run ensure_local_mesh_secrets.py manually"
fi
# Win parity: scripts/mesh/Invoke-MeshLocalCache.ps1 (platform/windows/install.ps1 -Mode Install)

# ─── Hermes harness (full repo checkout) ─────────────────────────────────────
LAN_ARCHIVE="$SCRIPT_DIR/scripts/mesh/lan_topology_archive.py"
if [[ -f "$LAN_ARCHIVE" ]]; then
  python3 "$LAN_ARCHIVE" --ensure-local-cache || warn "LAN topology archive step failed (mesh may need manual .env.local)"
fi
HARNESS_DIR="$SCRIPT_DIR/bin/orama-system/skills/hermes-harness/scripts"
VERIFY_TRUST="$SCRIPT_DIR/scripts/review/verify_trusted_install.py"

hermes_sync() {
  info "Syncing Hermes profiles from bin/agents staging ($1)..."
  if python3 "$HARNESS_DIR/install_hermes_profiles.py" --sync; then
    ok "Hermes profiles synced (or already matched staging)"
  else
    warn "Hermes profile sync failed — run manually after git pull"
  fi
  info "Syncing Hermes thin skill wrappers..."
  if python3 "$HARNESS_DIR/install_hermes_thin_skills.py" --verify; then
    ok "Hermes thin wrappers already synced"
  elif python3 "$HARNESS_DIR/install_hermes_thin_skills.py" --install --verify; then
    ok "Hermes thin wrappers installed"
  else
    warn "Hermes thin wrapper install failed — run install_hermes_thin_skills.py manually"
  fi
}

if [[ "${ORAMA_SKIP_HERMES_SYNC:-0}" == "1" ]]; then
  warn "Skipping Hermes harness sync (ORAMA_SKIP_HERMES_SYNC=1)"
elif [[ -f "$HARNESS_DIR/install_hermes_profiles.py" ]]; then
  export ORAMA_SYSTEM_PATH="$SCRIPT_DIR"
  if [[ "${ORAMA_TRUST_HERMES_SYNC:-}" == "1" ]]; then
    hermes_sync "operator-trusted override (ORAMA_TRUST_HERMES_SYNC=1)"
  elif [[ ! -f "$VERIFY_TRUST" ]]; then
    warn "Hermes sync skipped — verify_trusted_install.py missing (git pull --ff-only, or ORAMA_TRUST_HERMES_SYNC=1 after reviewing bin/agents)"
  elif ! python3 "$VERIFY_TRUST" --quiet; then
    warn "Hermes sync skipped — untrusted checkout (review bin/agents, git pull --ff-only on main, then ORAMA_TRUST_HERMES_SYNC=1)"
  else
    hermes_sync "idempotent, trusted checkout"
  fi
fi

# ─── steipete/agent-scripts bootstrap (opt-in, Phase 4) ─────────────────────
bootstrap_agent_scripts() {
  info "Bootstrapping steipete/agent-scripts (shared agent rules + skills)..."

  # No-op when git is missing
  if ! command -v git >/dev/null 2>&1; then
    warn "git not found on PATH — skipping steipete/agent-scripts bootstrap"
    return 0
  fi

  local target_dir="$AGENT_SCRIPTS_DIR"
  local target_link="$AGENT_SCRIPTS_LINK"

  # If the symlink already exists and points to the right place, refresh it
  if [[ -L "$target_link" ]]; then
    local current_target
    current_target="$(readlink "$target_link")"
    if [[ "$current_target" == "$target_dir" ]]; then
      info "steipete/agent-scripts symlink already present at $target_link"
      if git -C "$target_dir" pull --ff-only >/dev/null 2>&1; then
        ok "steipete/agent-scripts refreshed (--ff-only)"
      else
        warn "steipete/agent-scripts refresh failed — run: git -C $target_dir pull --ff-only"
      fi
      return 0
    else
      warn "$target_link exists but points to $current_target, not $target_dir — skipping"
      return 0
    fi
  fi

  # If a real directory exists at the link path, don't clobber it
  if [[ -e "$target_link" && ! -L "$target_link" ]]; then
    warn "$target_link exists and is not a symlink — skipping steipete/agent-scripts bootstrap"
    return 0
  fi

  # Clone the upstream repo (idempotent: no-op if already present)
  if [[ -d "$target_dir" && -d "$target_dir/.git" ]]; then
    info "steipete/agent-scripts already cloned at $target_dir — refreshing"
    if git -C "$target_dir" pull --ff-only >/dev/null 2>&1; then
      ok "steipete/agent-scripts refreshed (--ff-only)"
    else
      warn "steipete/agent-scripts refresh failed — run: git -C $target_dir pull --ff-only"
    fi
  else
    info "Cloning steipete/agent-scripts to $target_dir..."
    if git clone --depth 1 "$STEIPETE_REPO" "$target_dir" 2>/dev/null; then
      ok "steipete/agent-scripts cloned to $target_dir"
    else
      warn "steipete/agent-scripts clone failed — run manually: git clone $STEIPETE_REPO $target_dir"
      return 0
    fi
  fi

  # Create the symlink agents in this stack should follow
  mkdir -p "$(dirname "$target_link")"
  if ln -s "$target_dir" "$target_link" 2>/dev/null; then
    ok "steipete/agent-scripts symlinked at $target_link -> $target_dir"
  else
    warn "Could not create symlink $target_link -> $target_dir — create manually"
  fi

  info "NOTE: Never run scripts/sync-skills from this installer — it rewrites"
  info "      ~/.codex/skills and ~/.claude/skills and may collide with existing"
  info "      orama skill links. Run it manually after reviewing."
}

if [[ "${WITH_AGENT_SCRIPTS:-0}" == "1" ]]; then
  bootstrap_agent_scripts
fi

# ─── Verify ──────────────────────────────────────────────────────────────────
if [[ -f "$INSTALL_DIR/SKILL.md" ]]; then
  FILE_COUNT=$(find "$INSTALL_DIR" -type f | wc -l | tr -d ' ')
  echo ""
  echo -e "  ${GREEN}${BOLD}Installed successfully!${RESET}"
  echo -e "  ${GREEN}$FILE_COUNT files${RESET} -> ${BLUE}$INSTALL_DIR${RESET}"
  echo ""
  echo -e "  ${BOLD}Included:${RESET}"
  echo -e "    SKILL.md          Master methodology (5-stage + router + 6 directives)"
  echo -e "    afrp/             Audience-First Response Protocol (pre-router gate)"
  echo -e "    cidf/             Content Insertion Decision Framework v1.2"
  echo -e "    references/       5 deep-dive documents (progressive disclosure)"
  echo -e "    templates/        Task plan, verification checklist, lessons log"
  echo -e "    scripts/          verify_before_done.py, capture_lesson.py, create_task_plan.sh"
  echo -e "    config/           Agent registry + routing rules (Mode 3)"
  echo ""
  echo -e "  ${BOLD}How to use:${RESET}"
  echo -e "    Claude CLI:     Auto-activates on relevant queries"
  echo -e "    Manual load:    ${BLUE}/skill ultrathink${RESET} in Claude Code"
  echo ""

  # Layer 2: Claude Desktop MCPB (Perpetua-Tools — optional, no AlphaClaw required)
  PT_INSTALL=""
  for PT_CANDIDATE in \
    "${PERPETUA_TOOLS_PATH:-}" \
    "${PERPETUA_TOOLS_ROOT:-}" \
    "${OPENCLAW_HOME:-$HOME/openclaw-v1}/Perpetua-Tools" \
  ; do
    if [[ -n "$PT_CANDIDATE" && -f "$PT_CANDIDATE/install.sh" ]]; then
      PT_INSTALL="$PT_CANDIDATE/install.sh"
      break
    fi
  done
  if [[ -n "$PT_INSTALL" ]]; then
    info "Installing Claude Desktop LLM extensions (Perpetua-Tools MCPB)..."
    bash "$PT_INSTALL" --skip-desktop 2>/dev/null || warn "Perpetua-Tools MCPB install skipped (see Perpetua-Tools/install.sh)"
  fi
  echo ""
else
  echo -e "  ${RED}Installation failed — SKILL.md not found${RESET}"
  exit 1
fi
