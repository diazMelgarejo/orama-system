#!/usr/bin/env bash
# Resolve Perpetua-Tools hermes_harness.py with fail-closed PT root discovery.
# Git repo-relative crawl only — no hardcoded workstation layout paths.
# See ../references/workspace-path-resolution.md and
# ../../oramasys-method/references/sync-local-pt-checkout.md.
set -euo pipefail

# _is_pt_git_root verifies that a directory is a non-symlink Perpetua-Tools checkout containing the required Git metadata and application file.
_is_pt_git_root() {
  local d="${1%/}"
  [[ -n "$d" && -d "$d" ]] || return 1
  [[ -L "$d" ]] && return 1
  [[ -e "${d}/.git" && -f "${d}/orchestrator/fastapi_app.py" ]]
}

_pt_candidates=()

# _pt_add_candidate adds a valid, canonical Perpetua-Tools root to the candidate list when it is not already present.
_pt_add_candidate() {
  local d existing
  d="$(cd "${1%/}" 2>/dev/null && pwd)" || return 0
  _is_pt_git_root "$d" || return 0
  # bash 3.2 (macOS default) throws "unbound variable" on a bare
  # "${arr[@]}" expansion of a truly-empty array under set -u, even
  # though "${#arr[@]}" (count) is safe -- guard with the count check
  # before iterating. Confirmed empirically on bash 3.2.57.
  if ((${#_pt_candidates[@]} > 0)); then
    for existing in "${_pt_candidates[@]}"; do
      [[ "$existing" == "$d" ]] && return 0
    done
  fi
  _pt_candidates+=("$d")
}

_crawl_pt_git_roots_collect() {
  local base="${1%/}" depth="${2:-2}" d
  [[ -d "$base" ]] || return 0
  [[ -L "$base" ]] && return 0
  _pt_add_candidate "$base"
  if ((depth <= 0)); then
    return 0
  fi
  for d in "$base"/*/; do
    [[ -d "$d" ]] || continue
    [[ -L "$d" ]] && continue
    _pt_add_candidate "$d"
    _crawl_pt_git_roots_collect "$d" $((depth - 1))
  done
}

# _finalize_pt_root selects the sole valid Perpetua-Tools root and prints its path, failing when none or multiple roots are available.
_finalize_pt_root() {
  if ((${#_pt_candidates[@]} == 0)); then
    return 1
  fi
  if ((${#_pt_candidates[@]} > 1)); then
    echo "ERROR: ambiguous Perpetua-Tools roots (${#_pt_candidates[@]} marker-valid checkouts):" >&2
    printf '  %s\n' "${_pt_candidates[@]}" >&2
    return 1
  fi
  printf '%s\n' "${_pt_candidates[0]}"
}

_RESOLVED_PT_ROOT_CACHE=""

# resolve_pt_root resolves and prints the Perpetua-Tools repository root, using configured paths or filesystem discovery.
resolve_pt_root() {
  if [[ -n "${_RESOLVED_PT_ROOT_CACHE:-}" ]]; then
    echo "$_RESOLVED_PT_ROOT_CACHE"
    return 0
  fi
  local var v orama_root pt_dir mother pt_root
  local any_explicit_var_set=""
  for var in PERPETUA_TOOLS_PATH PT_HOME PERPETUA_TOOLS_ROOT PERPETUATOOLSROOT; do
    v="${!var:-}"
    if [[ -n "$v" ]]; then
      any_explicit_var_set=1
      if _is_pt_git_root "$v"; then
        _RESOLVED_PT_ROOT_CACHE="$(cd "$v" && pwd)"
        echo "$_RESOLVED_PT_ROOT_CACHE"
        return 0
      fi
    fi
  done
  if [[ -n "$any_explicit_var_set" ]]; then
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
    if [[ -n "$pt_dir" ]] && _is_pt_git_root "$pt_dir"; then
      _RESOLVED_PT_ROOT_CACHE="$(cd "$pt_dir" && pwd)"
      echo "$_RESOLVED_PT_ROOT_CACHE"
      return 0
    fi
  fi
  _pt_candidates=()
  if [[ -n "$orama_root" ]]; then
    mother="$(cd "$orama_root/.." && pwd)"
    _crawl_pt_git_roots_collect "$mother" 2
  fi
  _crawl_pt_git_roots_collect "$HOME" 3
  pt_root="$(_finalize_pt_root || true)"
  if [[ -n "$pt_root" ]]; then
    _RESOLVED_PT_ROOT_CACHE="$pt_root"
    echo "$_RESOLVED_PT_ROOT_CACHE"
    return 0
  fi
  return 1
}

# resolve_perp_harness_script resolves and prints the canonical path to the Perpetua-Tools Hermes harness script, or reports an error when the root or script cannot be found.
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
