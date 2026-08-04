# Sync local Perpetua-Tools checkout (cross-repo redirect stubs)

> **Use before loading a local canonical skill** from `perpetua-tools`,
> `perpetua-config`, or `perpetua-startup-intelligence` redirect stubs.
> **Fail closed:** on any check failure, use the GitHub `main` link from the stub
> instead of the local file.

Resolver order mirrors `scripts/discover.py`, `scripts/env/print-lan-peer-token.sh`,
and [`hermes-harness/references/workspace-path-resolution.md`](../../hermes-harness/references/workspace-path-resolution.md).

```bash
_is_pt_git_root() {
  local d="${1%/}"
  [[ -e "${d}/.git" && -f "${d}/orchestrator/fastapi_app.py" ]]
}

_crawl_pt_git_roots() {
  local base="${1%/}" depth="${2:-2}"
  local d
  if [[ ! -d "$base" ]]; then return 1; fi
  if _is_pt_git_root "$base"; then cd "$base" && pwd; return 0; fi
  if (( depth <= 0 )); then return 1; fi
  for d in "$base"/*/; do
    [[ -d "$d" ]] || continue
    if _is_pt_git_root "$d"; then cd "$d" && pwd; return 0; fi
    if _crawl_pt_git_roots "$d" $((depth - 1)); then return 0; fi
  done
  return 1
}

_resolve_pt_root() {
  for var in PERPETUATOOLSROOT PERPETUA_TOOLS_ROOT PERPETUA_TOOLS_PATH PT_HOME; do
    local v="${!var:-}"
    if [[ -n "$v" && _is_pt_git_root "$v" ]]; then echo "$v"; return 0; fi
  done
  local orama_root="${ORAMA_SYSTEM_PATH:-$(git rev-parse --show-toplevel 2>/dev/null || true)}"
  if [[ -n "$orama_root" && -f "$orama_root/.paths" ]]; then
    local pt_dir
    pt_dir="$(grep '^PT_DIR=' "$orama_root/.paths" | cut -d= -f2- | tr -d '"')"
    if [[ -n "$pt_dir" && _is_pt_git_root "$pt_dir" ]]; then echo "$pt_dir"; return 0; fi
  fi
  if [[ -n "$orama_root" ]]; then
    local mother
    mother="$(cd "$orama_root/.." && pwd)"
    if _crawl_pt_git_roots "$mother" 2; then return 0; fi
  fi
  _crawl_pt_git_roots "$HOME" 3
}

PT_ROOT="$(_resolve_pt_root || true)"
CANONICAL_PT_URL="${CANONICAL_PT_URL:-https://github.com/diazMelgarejo/Perpetua-Tools}"

if [[ -z "$PT_ROOT" ]]; then
  echo "No local PT clone resolved — use GitHub canonical: ${CANONICAL_PT_URL}"
  exit 1
fi

cd "$PT_ROOT" || { echo "Cannot cd PT_ROOT=$PT_ROOT — use ${CANONICAL_PT_URL}"; exit 1; }

if ! git fetch origin --prune; then
  echo "git fetch failed — use ${CANONICAL_PT_URL}"; exit 1
fi

branch="$(git symbolic-ref -q --short HEAD 2>/dev/null || true)"
upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
if [[ "$branch" != "main" || "$upstream" != "origin/main" ]]; then
  echo "Require main tracking origin/main (got branch=${branch:-?} upstream=${upstream:-none}) — use ${CANONICAL_PT_URL}"
  exit 1
fi

if git status --porcelain | grep -q .; then
  echo "Dirty worktree — stop; use safe-cross-host-sync with explicit operator approval, or ${CANONICAL_PT_URL}"
  exit 1
fi

if ! git pull --ff-only origin main; then
  echo "pull --ff-only origin main failed — use ${CANONICAL_PT_URL}"
  exit 1
fi

if git status --porcelain | grep -q .; then
  echo "Worktree dirty after pull — use ${CANONICAL_PT_URL}"
  exit 1
fi

echo "PT_ROOT=$PT_ROOT ready on origin/main"
```

Set `CANONICAL_PT_URL` to the stub-specific GitHub `blob/main/...` path before sourcing.
