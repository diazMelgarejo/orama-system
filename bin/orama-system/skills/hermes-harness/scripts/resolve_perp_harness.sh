#!/usr/bin/env bash
# Resolve Perpetua-Tools hermes_harness.py with fail-closed PT root discovery.
# Git repo-relative crawl only — no hardcoded workstation layout paths.
# See workspace-path-resolution.md and sync-local-pt-checkout.md.
set -euo pipefail

_is_pt_git_root() {
  local d="${1%/}"
  [[ -n "$d" && -d "$d" ]] || return 1
  [[ -L "$d" ]] && return 1
  [[ -e "${d}/.git" && -f "${d}/orchestrator/fastapi_app.py" ]]
}

_pt_candidates=()

_pt_add_candidate() {
  local d existing
  d="$(cd "${1%/}" 2>/dev/null && pwd)" || return 0
  _is_pt_git_root "$d" || return 0
  for existing in "${_pt_candidates[@]}"; do
    [[ "$existing" == "$d" ]] && return 0
  done
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

resolve_pt_root() {
  local var v orama_root pt_dir mother pt_root
  local any_explicit_var_set=""
  for var in PERPETUA_TOOLS_PATH PT_HOME PERPETUA_TOOLS_ROOT PERPETUATOOLSROOT; do
    v="${!var:-}"
    if [[ -n "$v" ]]; then
      any_explicit_var_set=1
      if _is_pt_git_root "$v"; then
        echo "$v"
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
      echo "$pt_dir"
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
