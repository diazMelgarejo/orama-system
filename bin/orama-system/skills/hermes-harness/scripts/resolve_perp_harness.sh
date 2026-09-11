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

# Accepted PT remote URL forms (https, ssh, and the short scp-like ssh
# form), case-insensitive host, optional trailing "/" or ".git". Anchored
# so "diazMelgarejo/Perpetua-Tools-fork" or a different org cannot match.
_PT_TRUSTED_REMOTE_PATTERN='^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)diazMelgarejo/Perpetua-Tools(\.git)?/?$'

# _pt_remote_trusted <dir>
#   Additive trust check, scoped to this resolver only (does not modify the
#   shared sibling_repo_is_git_root marker check other callers rely on).
#   A candidate that matches the marker file but has NO "origin" remote
#   configured is still accepted -- this preserves every existing
#   marker-only fixture/workflow (a fresh `git init` local checkout has no
#   remote at all) and matches this function's actual threat model: an
#   unrelated repo that happens to carry the marker file AND a real,
#   differently-owned remote is the concrete impersonation case this closes.
#   A candidate whose "origin" remote is set but does not match the trusted
#   pattern is rejected -- fail closed rather than silently trusting an
#   attacker-controlled or simply wrong upstream.
_pt_remote_trusted() {
  local dir="$1" remote_url
  remote_url="$(git -C "$dir" remote get-url origin 2>/dev/null || true)"
  [[ -z "$remote_url" ]] && return 0
  # GitHub's own host/org/repo routing is case-insensitive (GITHUB.com and
  # github.com resolve identically), so a case-sensitive `[[ =~ ]]` here
  # would wrongly reject a legitimately-configured remote that happens to
  # differ only in case. nocasematch is restored unconditionally via the
  # trap-free save/restore below, including on the early-return path.
  local _was_nocasematch=0
  shopt -q nocasematch && _was_nocasematch=1
  shopt -s nocasematch
  [[ "$remote_url" =~ $_PT_TRUSTED_REMOTE_PATTERN ]]
  local _matched=$?
  ((_was_nocasematch)) || shopt -u nocasematch
  return "$_matched"
}

# resolve_pt_root resolves and prints the Perpetua-Tools repository root,
# using configured paths, the orama .paths cache, or filesystem discovery.
# Memoizes into _RESOLVED_PT_ROOT_CACHE so repeated calls in the same shell
# don't re-crawl.
resolve_pt_root() {
  if [[ -n "${_RESOLVED_PT_ROOT_CACHE:-}" ]]; then
    if sibling_repo_is_git_root "$_RESOLVED_PT_ROOT_CACHE" "$_PT_MARKER" \
      && _pt_remote_trusted "$_RESOLVED_PT_ROOT_CACHE"; then
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
    if _pt_remote_trusted "$path"; then
      _RESOLVED_PT_ROOT_CACHE="$(cd "$path" && pwd)"
      echo "$_RESOLVED_PT_ROOT_CACHE"
      return 0
    fi
    # Same fail-closed posture as the override_rc==2 branch below: an
    # explicit override resolved to a marker-valid git root, but its
    # "origin" remote does not match the trusted Perpetua-Tools pattern.
    # Do not silently fall through to .paths/crawl discovery for some
    # other checkout -- report exactly why this one was rejected.
    echo "resolve_pt_root: override resolved to ${path} but its origin remote is not a trusted Perpetua-Tools remote" >&2
    return 1
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
    if [[ -n "$pt_dir" ]] && sibling_repo_is_git_root "$pt_dir" "$_PT_MARKER" \
      && _pt_remote_trusted "$pt_dir"; then
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
  if [[ -n "$pt_root" ]] && _pt_remote_trusted "$pt_root"; then
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
