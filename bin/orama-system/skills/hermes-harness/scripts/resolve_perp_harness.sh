#!/usr/bin/env bash
# Resolve Perpetua-Tools hermes_harness.py with fail-closed PT root discovery.
# Git repo-relative crawl only — no hardcoded workstation layout paths.
# See workspace-path-resolution.md and sync-local-pt-checkout.md.
set -euo pipefail

_is_pt_git_root() {
  local d="${1%/}"
  [[ -e "${d}/.git" && -f "${d}/orchestrator/fastapi_app.py" ]]
}

_crawl_pt_git_roots() {
  local base="${1%/}" depth="${2:-2}"
  local d sub
  if [[ ! -d "$base" ]]; then
    return 1
  fi
  if _is_pt_git_root "$base"; then
    cd "$base" && pwd
    return 0
  fi
  if (( depth <= 0 )); then
    return 1
  fi
  for d in "$base"/*/; do
    [[ -d "$d" ]] || continue
    if _is_pt_git_root "$d"; then
      cd "$d" && pwd
      return 0
    fi
    if _crawl_pt_git_roots "$d" $((depth - 1)); then
      return 0
    fi
  done
  return 1
}

resolve_pt_root() {
  local var v orama_root pt_dir mother
  for var in PERPETUATOOLSROOT PERPETUA_TOOLS_ROOT PERPETUA_TOOLS_PATH PT_HOME; do
    v="${!var:-}"
    if [[ -n "$v" ]] && _is_pt_git_root "$v"; then
      echo "$v"
      return 0
    fi
  done
  orama_root="${ORAMA_SYSTEM_PATH:-$(git rev-parse --show-toplevel 2>/dev/null || true)}"
  if [[ -n "$orama_root" && -f "$orama_root/.paths" ]]; then
    pt_dir="$(grep '^PT_DIR=' "$orama_root/.paths" | cut -d= -f2- | tr -d '"')"
    if [[ -n "$pt_dir" ]] && _is_pt_git_root "$pt_dir"; then
      echo "$pt_dir"
      return 0
    fi
  fi
  if [[ -n "$orama_root" ]]; then
    mother="$(cd "$orama_root/.." && pwd)"
    if _crawl_pt_git_roots "$mother" 2; then
      return 0
    fi
  fi
  _crawl_pt_git_roots "$HOME" 3
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
