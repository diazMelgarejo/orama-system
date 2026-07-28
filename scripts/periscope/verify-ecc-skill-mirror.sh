#!/usr/bin/env bash
# Idempotent probe: verify periscope ECC mirrored skills are byte-identical.
# No install, no mutation. SKIP (exit 0) when periscope ECC paths are absent.
set -euo pipefail

log() { printf '%s\n' "$*"; }

resolve_periscope_repo() {
  if [[ -n "${PERISCOPE_REPO:-}" ]]; then
    printf '%s' "$PERISCOPE_REPO"
    return 0
  fi
  if [[ -n "${OPENCLAW_HOME:-}" ]] \
    && [[ -f "$OPENCLAW_HOME/periscope/.agents/skills/periscope/SKILL.md" ]]; then
    printf '%s' "$OPENCLAW_HOME/periscope"
    return 0
  fi
  return 1
}

REQUESTED_REPO="${PERISCOPE_REPO:-}"
PERISCOPE_REPO="$(resolve_periscope_repo || true)"

if [[ -n "$REQUESTED_REPO" ]]; then
  if [[ ! -d "$PERISCOPE_REPO" ]] || [[ ! -r "$PERISCOPE_REPO" ]]; then
    log "periscope ECC: configured repository is missing or inaccessible: $REQUESTED_REPO" >&2
    exit 1
  fi
fi

if [[ -z "$PERISCOPE_REPO" ]]; then
  log "periscope ECC: not present — SKIP sidecar"
  exit 0
fi

AGENTS_SKILL="${PERISCOPE_REPO}/.agents/skills/periscope/SKILL.md"
CLAUDE_SKILL="${PERISCOPE_REPO}/.claude/skills/periscope/SKILL.md"
INSTINCTS="${PERISCOPE_REPO}/.claude/homunculus/instincts/inherited/periscope-instincts.yaml"

if [[ -n "$REQUESTED_REPO" ]] && [[ ! -f "$AGENTS_SKILL" ]]; then
  log "periscope ECC: configured repository lacks the Agents skill: $REQUESTED_REPO" >&2
  exit 1
fi

if [[ ! -f "$AGENTS_SKILL" ]]; then
  log "periscope ECC: not present — SKIP sidecar"
  exit 0
fi

if [[ ! -f "$CLAUDE_SKILL" ]]; then
  log "periscope ECC: missing Claude mirror: $CLAUDE_SKILL" >&2
  exit 1
fi

if ! cmp -s "$AGENTS_SKILL" "$CLAUDE_SKILL"; then
  log "periscope ECC: mirror drift between Agents and Claude skills" >&2
  log "  agents: $AGENTS_SKILL" >&2
  log "  claude: $CLAUDE_SKILL" >&2
  exit 1
fi

log "periscope ECC: mirror OK ($PERISCOPE_REPO)"

if [[ -f "$INSTINCTS" ]]; then
  missing=0
  for id in \
    periscope-workflow-dependency-update \
    periscope-instinct-dependency-update; do
    if ! grep -q "^id: ${id}$" "$INSTINCTS"; then
      log "periscope ECC: missing instinct id: $id" >&2
      missing=1
    fi
  done
  if [[ "$missing" -eq 1 ]]; then
    exit 1
  fi
  log "periscope ECC: dependency instinct pair present"
fi

exit 0
