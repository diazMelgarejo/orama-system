#!/usr/bin/env bash
# ensure_cline_cli.sh — Idempotent install/update check for the Cline CLI (npm: cline).
#
# Called by bind_cline_backend.sh before its `command -v cline` gate, so
# reconciling cline-agent also self-heals a missing or stale CLI instead of
# just reporting needs_cline and giving up.
#
# Pattern: compare the installed version against the npm registry via
# `npm view cline version` (a lightweight metadata query, no download) and
# skip reinstall when they already match. Guards `command -v cline` before
# calling `cline --version` so a missing binary never raises. Fails open
# (keeps whatever is already installed, or leaves it absent) if the npm
# registry is unreachable, rather than blocking agent reconciliation on a
# network check.
#
# All output goes to stderr — bind_cline_backend.sh's stdout is a JSON
# status contract and must not be polluted. Always exits 0 (fail-open);
# the caller re-checks `command -v cline` afterward to decide next steps.
#
# Captured as PT .agent memory lesson_6125fbdf46ec.

set -euo pipefail

log() { printf '[ensure-cline-cli] %s\n' "$*" >&2; }

if ! command -v npm >/dev/null 2>&1; then
  log "npm not found — skipping (Cline CLI requires Node >= 18 + npm)."
  exit 0
fi

INSTALLED_VERSION=""
if command -v cline >/dev/null 2>&1; then
  INSTALLED_VERSION="$(cline --version 2>/dev/null | head -1 | tr -d '[:space:]')"
fi

REGISTRY_VERSION="$(npm view cline version 2>/dev/null || true)"

if [ -z "$REGISTRY_VERSION" ]; then
  # Registry unreachable (offline, DNS, npm outage) — fail open, keep current state.
  if [ -n "$INSTALLED_VERSION" ]; then
    log "npm registry unreachable — keeping installed cline@$INSTALLED_VERSION as-is."
  else
    log "npm registry unreachable and cline not installed — skipping (offline)."
  fi
  exit 0
fi

if [ -n "$INSTALLED_VERSION" ] && [ "$INSTALLED_VERSION" = "$REGISTRY_VERSION" ]; then
  log "cline@$INSTALLED_VERSION already up to date (registry: $REGISTRY_VERSION)."
  exit 0
fi

if [ -n "$INSTALLED_VERSION" ]; then
  log "cline@$INSTALLED_VERSION installed, registry has $REGISTRY_VERSION — updating..."
else
  log "cline not found — installing $REGISTRY_VERSION..."
fi

if npm install -g cline >/dev/null 2>&1; then
  NEW_VERSION="$(command -v cline >/dev/null 2>&1 && cline --version 2>/dev/null | head -1 | tr -d '[:space:]' || echo "$REGISTRY_VERSION")"
  log "cline@$NEW_VERSION ready."
else
  log "npm install -g cline failed — leaving existing state (${INSTALLED_VERSION:-not installed}) in place."
fi

exit 0
