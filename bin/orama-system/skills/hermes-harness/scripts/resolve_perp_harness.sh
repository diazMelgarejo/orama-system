#!/usr/bin/env bash
# Resolve Perpetua-Tools hermes_harness.py with fail-closed PT root discovery.
# See workspace-path-resolution.md and sync-local-pt-checkout.md.
set -euo pipefail

resolve_pt_root() {
  local var v orama_root pt_dir fallback
  for var in PERPETUATOOLSROOT PERPETUA_TOOLS_ROOT PERPETUA_TOOLS_PATH PT_HOME; do
    v="${!var:-}"
    if [[ -n "$v" && -e "$v/.git" ]]; then
      echo "$v"
      return 0
    fi
  done
  orama_root="${ORAMA_SYSTEM_PATH:-$(git rev-parse --show-toplevel 2>/dev/null || true)}"
  if [[ -n "$orama_root" && -f "$orama_root/.paths" ]]; then
    pt_dir="$(grep '^PT_DIR=' "$orama_root/.paths" | cut -d= -f2- | tr -d '"')"
    if [[ -n "$pt_dir" && -e "$pt_dir/.git" ]]; then
      echo "$pt_dir"
      return 0
    fi
  fi
  fallback="${OPENCLAW_HOME:-$HOME}/Perpetua-Tools"
  if [[ -e "$fallback/.git" ]]; then
    echo "$fallback"
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
