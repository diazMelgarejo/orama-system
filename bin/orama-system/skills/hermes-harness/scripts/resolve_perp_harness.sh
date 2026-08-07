#!/usr/bin/env bash
# Resolve Perpetua-Tools hermes_harness.py with fail-closed PT root discovery.
# Git repo-relative crawl only — no hardcoded workstation layout paths.
# See workspace-path-resolution.md and sync-local-pt-checkout.md.
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

resolve_pt_root() {
  local override_rc=0 pt_dir orama_root mother pt_root path
  path="$(sibling_repo_check_env_override "$_PT_MARKER" \
    PERPETUA_TOOLS_PATH PT_HOME PERPETUA_TOOLS_ROOT PERPETUATOOLSROOT)" || override_rc=$?
  if ((override_rc == 0)); then
    echo "$path"
    return 0
  elif ((override_rc == 2)); then
    # An explicit override was configured (PERPETUA_TOOLS_PATH / PT_HOME /
    # PERPETUA_TOOLS_ROOT / PERPETUATOOLSROOT) but none resolved to a valid,
    # non-symlinked PT git root. Fail closed here rather than falling
    # through to .paths/crawl discovery -- silently ignoring an explicit,
    # broken override to go find *some other* PT checkout elsewhere on the
    # machine is surprising and can silently resolve to the wrong repo.
    return 1
  fi
  orama_root="${ORAMA_SYSTEM_PATH:-$(git rev-parse --show-toplevel 2>/dev/null || true)}"
  if [[ -n "$orama_root" && -f "$orama_root/.paths" ]]; then
    pt_dir="$(grep '^PT_DIR=' "$orama_root/.paths" | cut -d= -f2- | tr -d '"')"
    if [[ -n "$pt_dir" ]] && sibling_repo_is_git_root "$pt_dir" "$_PT_MARKER"; then
      echo "$pt_dir"
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
    echo "$pt_root"
    return 0
  fi
  return 1
}

resolve_perp_harness_script() {
  local pt_root script
  pt_root="$(resolve_pt_root || true)"
  if [[ -z "$pt_root" ]]; then
    echo "ERROR: Perpetua-Tools root not resolved. Clone PT and set PERPETUA_TOOLS_ROOT, or see sync-local-pt-checkout.md." >&2
    return 1
  fi
  script="${pt_root}/src/hermes_harness.py"
  if [[ ! -f "$script" ]]; then
    echo "ERROR: hermes_harness.py not found at ${script}" >&2
    return 1
  fi
  python3 -c "import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())" "$script"
}
