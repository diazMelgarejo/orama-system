#!/usr/bin/env bash
# Recreate mistaken main-target deps/docs PRs as ordered branches → base merged.
#
# Merge order (into `merged` only):
#   1. onto-merged/01-deps-cargo-tauri     — cargo / tauri 2.11.1 (required)
#   2. onto-merged/02-deps-npm-svelte-postcss — svelte + postcss only (not full deps/2)
#   3. onto-merged/03-docs-cursor-cloud-agents — AGENTS.md Cursor Cloud section
#
# Also: close dependabot PRs #5/#6 (base main); supersede #1–#3.
# Identity: cyre <diazMelgarejo@gmail.com> or Lawrence@cyre.me — no Co-authored-by trailers.
set -euo pipefail

REPO="${PERISCOPE_REPO:-$HOME/Documents/oramasys/tools/periscope}"
ORIGIN="${PERISCOPE_ORIGIN:-https://github.com/diazMelgarejo/periscope.git}"
ORAMA_ROOT="${ORAMA_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
CARGO_SRC_BRANCH="${CARGO_SRC_BRANCH:-deps/3-cargo-tauri-onto-merged}"
DOCS_SRC_SHA="${DOCS_SRC_SHA:-73eb23d12a0d02e3cce9b0f6bee915871726b4e0}"

log() { printf '>>> %s\n' "$*"; }

if [[ ! -d "$REPO/.git" ]]; then
  log "clone -> $REPO"
  mkdir -p "$(dirname "$REPO")"
  git clone "$ORIGIN" "$REPO"
fi

cd "$REPO"
git config user.name "${GIT_AUTHOR_NAME:-cyre}"
git config user.email "${GIT_AUTHOR_EMAIL:-diazMelgarejo@gmail.com}"

git fetch origin merged "$CARGO_SRC_BRANCH" cursor/env-setup-cloud-instructions-76c9 2>/dev/null || \
  git fetch origin merged "$CARGO_SRC_BRANCH" 2>/dev/null || git fetch origin merged

BASE="$(git rev-parse origin/merged)"
log "base merged = $BASE"

# --- 0/3 cursor rules + git (from orama-system) ---
log "[0/3] onto-merged/00-cursor-openclaw-rules"
if [[ -x "$ORAMA_ROOT/scripts/periscope/install-cursor-rules.sh" ]]; then
  PERISCOPE_REPO="$REPO" ORAMA_ROOT="$ORAMA_ROOT" bash "$ORAMA_ROOT/scripts/periscope/install-cursor-rules.sh"
  git checkout -B onto-merged/00-cursor-openclaw-rules "$BASE"
  git add .cursor/rules scripts/git AGENTS.md
  if ! git diff --cached --quiet; then
    git commit -m "chore(cursor): OpenClaw Cursor rules + git guards (orama-aligned)"
  fi
  git push -u origin onto-merged/00-cursor-openclaw-rules --force-with-lease
  gh pr create --repo diazMelgarejo/periscope --base merged --head onto-merged/00-cursor-openclaw-rules \
    --title "[0/3 → merged] chore: Cursor rules + git guards (orama-aligned)" \
    --body "From orama-system install-cursor-rules.sh. Optional first merge." \
    || log "PR [0/3] may already exist"
else
  log "skip [0/3]: orama install-cursor-rules.sh not found at $ORAMA_ROOT"
fi

# --- 1/3 cargo ---
log "[1/3] onto-merged/01-deps-cargo-tauri"
git checkout -B onto-merged/01-deps-cargo-tauri "$BASE"
CARGO_COMMIT="$(git rev-parse "origin/$CARGO_SRC_BRANCH")"
git cherry-pick "$CARGO_COMMIT"
git commit --amend --author="cyre <diazMelgarejo@gmail.com>" --no-edit
git push -u origin onto-merged/01-deps-cargo-tauri --force-with-lease

gh pr close 6 --repo diazMelgarejo/periscope --comment "Superseded by [1/3] PR base merged (onto-merged/01-deps-cargo-tauri)." 2>/dev/null || true

gh pr create --repo diazMelgarejo/periscope \
  --base merged \
  --head onto-merged/01-deps-cargo-tauri \
  --title "[1/3 → merged] build(deps): cargo / tauri 2.11.1" \
  --body "Required step 1 of 3. Replaces mistaken main-target PR #3/#6.

**Merge first** into \`merged\`. Do not merge to \`main\`." \
  || log "PR [1/3] may already exist"

# --- 2/3 targeted npm (rebase on 1 if already merged, else on merged) ---
log "[2/3] onto-merged/02-deps-npm-svelte-postcss"
if git rev-parse origin/onto-merged/01-deps-cargo-tauri >/dev/null 2>&1; then
  git checkout -B onto-merged/02-deps-npm-svelte-postcss origin/onto-merged/01-deps-cargo-tauri
else
  git checkout -B onto-merged/02-deps-npm-svelte-postcss "$BASE"
fi
if [[ ! -d frontend/package.json ]]; then
  echo "missing frontend/" >&2
  exit 1
fi
(
  cd frontend
  npm install "svelte@5.55.9" --save-dev
  npm install "postcss@8.5.15" 2>/dev/null || npm update postcss
)
# Keep marked pinned — do not downgrade
if grep -q '"marked": "18.0.3"' frontend/package.json; then
  log "marked 18.0.3 preserved"
fi
git add frontend/package.json frontend/package-lock.json
git commit -m "build(deps): bump svelte and postcss in frontend (onto merged, 2/3)

Targeted npm only — marked unchanged. Merge after [1/3] cargo PR."
git push -u origin onto-merged/02-deps-npm-svelte-postcss --force-with-lease

gh pr close 5 --repo diazMelgarejo/periscope --comment "Superseded by [2/3] PR base merged (onto-merged/02-deps-npm-svelte-postcss)." 2>/dev/null || true

gh pr create --repo diazMelgarejo/periscope \
  --base merged \
  --head onto-merged/02-deps-npm-svelte-postcss \
  --title "[2/3 → merged] build(deps): svelte + postcss (targeted npm)" \
  --body "Step 2 of 3. Does **not** include the old \`deps/2-npm-frontend-onto-merged\` branch (avoid marked downgrade).

Merge after [1/3]." \
  || log "PR [2/3] may already exist"

# --- 3/3 AGENTS.md ---
log "[3/3] onto-merged/03-docs-cursor-cloud-agents"
git checkout -B onto-merged/03-docs-cursor-cloud-agents "$BASE"
if ! grep -q "## Cursor Cloud specific instructions" AGENTS.md; then
  python3 - "$DOCS_SRC_SHA" <<'PY'
import subprocess, sys
sha = sys.argv[1]
text = subprocess.check_output(["git", "show", f"{sha}:AGENTS.md"], text=True)
marker = "## Cursor Cloud specific instructions"
if marker not in text:
    sys.exit("marker not in source AGENTS.md")
section = text[text.index(marker):]
from pathlib import Path
p = Path("AGENTS.md")
p.write_text(p.read_text().rstrip() + "\n\n" + section + "\n")
print("appended Cursor Cloud section")
PY
  git add AGENTS.md
  git commit -m "docs(agents): Cursor Cloud instructions (onto merged, 3/3)

Salvaged single-file from former PR #4; base is merged (not stale env-setup branch)."
else
  log "AGENTS.md already has Cursor Cloud section — skip commit"
fi
git push -u origin onto-merged/03-docs-cursor-cloud-agents --force-with-lease

gh pr create --repo diazMelgarejo/periscope \
  --base merged \
  --head onto-merged/03-docs-cursor-cloud-agents \
  --title "[3/3 → merged] docs: Cursor Cloud AGENTS.md section" \
  --body "Step 3 of 3. Cherry-pick content only (not branch \`cursor/env-setup-cloud-instructions-76c9\`).

Merge after [2/3]. Replaces closed PR #4." \
  || log "PR [3/3] may already exist"

log "Done. Close old branches: deps/2-npm-frontend-onto-merged, deps/3-cargo-tauri-onto-merged (optional)."
log "PR titles: [1/3 → merged] … [2/3 → merged] … [3/3 → merged] …"
