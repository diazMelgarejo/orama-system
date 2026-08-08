#!/usr/bin/env bash
# Resolve Perpetua-Tools hermes_harness.py with fail-closed PT root discovery.
# Git repo-relative crawl only — no hardcoded workstation layout paths.
# See ../references/workspace-path-resolution.md and
# ../../oramasys-method/references/sync-local-pt-checkout.md.
#
# Thin wrapper over scripts/git/resolve_sibling_git_repo.sh's generic
# marker-based crawler (see that file for why: a fixed relative-depth
# assumption breaks once a sibling repo is nested deeper than expected).
set -euo pipefail

_RPH_SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_RPH_REPO_ROOT="$(cd "$_RPH_SELF_DIR" && git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -n "$_RPH_REPO_ROOT" && -f "$_RPH_REPO_ROOT/scripts/git/resolve_sibling_git_repo.sh" ]]; then
  # shellcheck source=../../../../../scripts/git/resolve_sibling_git_repo.sh
  source "$_RPH_REPO_ROOT/scripts/git/resolve_sibling_git_repo.sh"
else
  echo "ERROR: resolve_sibling_git_repo.sh not found under repo root ${_RPH_REPO_ROOT:-<unresolved>}" >&2
  return 1 2>/dev/null || exit 1
fi

_PT_MARKER="orchestrator/fastapi_app.py"
_RESOLVED_PT_ROOT_CACHE=""

# resolve_pt_root resolves and prints the Perpetua-Tools repository root,
# using configured paths, the orama .paths cache, or filesystem discovery.
# Memoizes into _RESOLVED_PT_ROOT_CACHE so repeated calls in the same shell
# don't re-crawl.
resolve_pt_root() {
  if [[ -n "${_RESOLVED_PT_ROOT_CACHE:-}" ]]; then
    if sibling_repo_is_git_root "$_RESOLVED_PT_ROOT_CACHE" "$_PT_MARKER"; then
      echo "$_RESOLVED_PT_ROOT_CACHE"
      return 0
    fi
    # Cached path no longer resolves (moved, removed, or an override was
    # reconfigured after the first call in this shell) -- invalidate rather
    # than trust a stale value silently. Mirror of the same fix in PT's
    # scripts/resolve_orama_root.sh::resolve_orama_root.
    _RESOLVED_PT_ROOT_CACHE=""
  fi
  local override_rc=0 pt_dir orama_root mother pt_root path
  path="$(sibling_repo_check_env_override "$_PT_MARKER" \
    PERPETUA_TOOLS_PATH PT_HOME PERPETUA_TOOLS_ROOT PERPETUATOOLSROOT)" || override_rc=$?
  if ((override_rc == 0)); then
    _RESOLVED_PT_ROOT_CACHE="$(cd "$path" && pwd)"
    echo "$_RESOLVED_PT_ROOT_CACHE"
    return 0
  elif ((override_rc == 2)); then
    # An explicit override was configured (PERPETUA_TOOLS_PATH / PT_HOME /
    # PERPETUA_TOOLS_ROOT / PERPETUATOOLSROOT) but none resolved to a valid,
    # non-symlinked PT git root. Fail closed here rather than falling
    # through to .paths/crawl discovery -- silently ignoring an explicit,
    # broken override to go find *some other* PT checkout elsewhere on the
    # machine is surprising and can silently resolve to the wrong repo. Trace
    # exactly what each candidate var held so this is debuggable.
    echo "resolve_pt_root: PERPETUA_TOOLS_PATH/PT_HOME/PERPETUA_TOOLS_ROOT/PERPETUATOOLSROOT is set but did not resolve to a valid Perpetua-Tools checkout (missing ${_PT_MARKER} or not a git root) -- PERPETUA_TOOLS_PATH=${PERPETUA_TOOLS_PATH:-<unset>} PT_HOME=${PT_HOME:-<unset>} PERPETUA_TOOLS_ROOT=${PERPETUA_TOOLS_ROOT:-<unset>} PERPETUATOOLSROOT=${PERPETUATOOLSROOT:-<unset>}" >&2
    return 1
  fi
  orama_root="${ORAMA_SYSTEM_PATH:-$(git rev-parse --show-toplevel 2>/dev/null || true)}"
  if [[ -n "$orama_root" && -f "$orama_root/.paths" ]]; then
    pt_dir="$(grep '^PT_DIR=' "$orama_root/.paths" | cut -d= -f2- | tr -d '"')"
    if [[ -n "$pt_dir" ]] && sibling_repo_is_git_root "$pt_dir" "$_PT_MARKER"; then
      _RESOLVED_PT_ROOT_CACHE="$(cd "$pt_dir" && pwd)"
      echo "$_RESOLVED_PT_ROOT_CACHE"
      return 0
    fi
  fi
  sibling_repo_reset_candidates
  if [[ -n "$orama_root" ]]; then
    mother="$(cd "$orama_root/.." && pwd)"
    sibling_repo_crawl_collect "$mother" "$_PT_MARKER" 2
  fi
  sibling_repo_crawl_collect "$HOME" "$_PT_MARKER" 3
  pt_root="$(sibling_repo_finalize "Perpetua-Tools" || true)"
  if [[ -n "$pt_root" ]]; then
    _RESOLVED_PT_ROOT_CACHE="$pt_root"
    echo "$_RESOLVED_PT_ROOT_CACHE"
    return 0
  fi
  return 1
}

# resolve_perp_harness_script resolves and prints the canonical path to the
# Perpetua-Tools Hermes harness script, or reports an error when the root or
# script cannot be found.
resolve_perp_harness_script() {
  local pt_root script
  pt_root="$(resolve_pt_root || true)"
  if [[ -z "$pt_root" ]]; then
    echo "ERROR: Perpetua-Tools root not resolved. Clone PT and set PERPETUA_TOOLS_ROOT, or see ../../oramasys-method/references/sync-local-pt-checkout.md." >&2
    return 1
  fi
  script="${pt_root}/src/hermes_harness.py"
  if [[ ! -f "$script" ]]; then
    echo "ERROR: hermes_harness.py not found at ${script}" >&2
    return 1
  fi
  python3 -c "import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())" "$script"
}
