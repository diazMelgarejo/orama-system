#!/usr/bin/env bash
# Full history expunge: metadata remap + message/blob literal scrub via git-filter-repo,
# then filter-branch env/msg pass for broken Co-authored-by remnants.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${1:-}" && -d "${1}/.git" ]]; then
  REPO_ROOT="$(cd "$1" && pwd)"
else
  REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

export PATH="${HOME:-/home/ubuntu}/.local/bin:${PATH}"

# shellcheck source=banned_attribution_lib.sh
source "$SCRIPT_DIR/banned_attribution_lib.sh"

cd "$REPO_ROOT"

if [[ -x scripts/cursor/sync-private-attribution-from-home.sh ]]; then
  bash scripts/cursor/sync-private-attribution-from-home.sh
elif [[ -x scripts/cursor/write-openclaw-private-attribution.sh ]]; then
  bash scripts/cursor/write-openclaw-private-attribution.sh
fi

bash "$SCRIPT_DIR/sync-banned-patterns-to-repo.sh" "$REPO_ROOT"

if ! banned_patterns_ready "$REPO_ROOT"; then
  echo "ERROR: banned-attribution patterns missing for $REPO_ROOT" >&2
  exit 1
fi

if ! command -v git-filter-repo >/dev/null 2>&1; then
  echo "ERROR: git-filter-repo not installed (pip install git-filter-repo)" >&2
  exit 1
fi

OPENCLAW="${HOME:-/home/ubuntu}/.cursor/openclaw"
mkdir -p "$OPENCLAW"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
MAILMAP="${OPENCLAW}/${REPO_ROOT##*/}-expunge-${STAMP}.mailmap"
REPLACE_MSG="${OPENCLAW}/${REPO_ROOT##*/}-expunge-${STAMP}-replace-message.txt"
REPLACE_TEXT="${OPENCLAW}/${REPO_ROOT##*/}-expunge-${STAMP}-replace-text.txt"

python3 - "$MAILMAP" "$REPLACE_MSG" "$REPLACE_TEXT" "$REPO_ROOT" <<'PY'
import re
import sys
from pathlib import Path

mailmap_path, replace_msg_path, replace_text_path, repo_root = sys.argv[1:5]
repo = Path(repo_root)

def load_tokens():
    patterns = Path.home() / ".cursor/openclaw/banned-attribution-patterns"
    tokens = []
    for line in patterns.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            tokens.append(line)
    verboten = repo
    while verboten != verboten.parent:
        vf = verboten / ".verboten-literals.local"
        if vf.is_file():
            for raw in vf.read_text(encoding="utf-8").splitlines():
                raw = raw.split("#", 1)[0].strip()
                if raw.startswith("forbidden_attribution="):
                    val = raw.split("=", 1)[1].strip()
                    if val:
                        tokens.append(val)
            break
        if (verboten / "orama-system").is_dir():
            vf = verboten / ".verboten-literals.local"
            if vf.is_file():
                for raw in vf.read_text(encoding="utf-8").splitlines():
                    raw = raw.split("#", 1)[0].strip()
                    if raw.startswith("forbidden_attribution="):
                        val = raw.split("=", 1)[1].strip()
                        if val:
                            tokens.append(val)
            break
        verboten = verboten.parent
    # de-dupe case-insensitive
    seen = set()
    out = []
    for t in tokens:
        k = t.casefold()
        if k in seen:
            continue
        seen.add(k)
        out.append(t)
    return out

tokens = load_tokens()
if not tokens:
    raise SystemExit("no tokens for expunge filters")

mailmap_lines = []
for tok in tokens:
    mailmap_lines.append(f"cyre <diazmelgarejo@gmail.com> <{tok}@gmail.com>")
    mailmap_lines.append(f"cyre <diazmelgarejo@gmail.com> {tok} <{tok}@gmail.com>")
Path(mailmap_path).write_text("\n".join(mailmap_lines) + "\n", encoding="utf-8")

replace_msg = ["# Auto-generated expunge rules — local only"]
replace_text = ["***REMOVED***"]
for tok in tokens:
    esc = re.escape(tok)
    replace_msg.append(f"regex:(?i){esc}==>")
    replace_msg.append(f"regex:(?i)^Co-authored-by:.*{esc}.*\\n==>")
    replace_text.append(f"literal:{tok}==>REDACTED")
Path(replace_msg_path).write_text("\n".join(replace_msg) + "\n", encoding="utf-8")
Path(replace_text_path).write_text("\n".join(replace_text) + "\n", encoding="utf-8")
print(f"tokens={len(tokens)}")
PY

REMOTE_URL=""
if git remote get-url origin >/dev/null 2>&1; then
  REMOTE_URL="$(git remote get-url origin)"
fi

TAG="pre-expunge-backup-${STAMP}"
git tag "$TAG" HEAD

echo ">>> filter-repo (mailmap + message + blob replace)"
git filter-repo --force \
  --mailmap "$MAILMAP" \
  --replace-message "$REPLACE_MSG" \
  --replace-text "$REPLACE_TEXT"

MSG_FILTER="$SCRIPT_DIR/filter-msg-strip-banned.sh"
ENV_FILTER="$SCRIPT_DIR/filter-env-scrub-banned.sh"
chmod +x "$MSG_FILTER" "$ENV_FILTER"
export FILTER_BRANCH_SQUELCH_WARNING=1
echo ">>> filter-branch (author/committer + co-author remnants)"
git filter-branch -f \
  --env-filter "REPO_ROOT='$REPO_ROOT' bash '$ENV_FILTER'" \
  --msg-filter "REPO_ROOT='$REPO_ROOT' bash '$MSG_FILTER'" \
  --tag-name-filter cat -- --all

git for-each-ref --format='%(refname)' refs/original/ 2>/dev/null | while read -r ref; do
  git update-ref -d "$ref" 2>/dev/null || true
done

git reflog expire --expire=now --all
git gc --prune=now --aggressive

while IFS= read -r h; do
  ae_lc="$(git log -1 --format=%ae "$h" | tr '[:upper:]' '[:lower:]')"
  an_lc="$(git log -1 --format=%an "$h" | tr '[:upper:]' '[:lower:]')"
  ce_lc="$(git log -1 --format=%ce "$h" | tr '[:upper:]' '[:lower:]')"
  cn_lc="$(git log -1 --format=%cn "$h" | tr '[:upper:]' '[:lower:]')"
  body_lc="$(git log -1 --format=%B "$h" | tr '[:upper:]' '[:lower:]')"
  if metadata_contains_scrub_target "$ae_lc" "$an_lc" "$ce_lc" "$cn_lc" "$body_lc" "$REPO_ROOT"; then
    echo "FAIL: banned attribution metadata still on $h" >&2
    exit 1
  fi
done < <(git rev-list --all)

if [[ -n "$REMOTE_URL" ]]; then
  git remote add origin "$REMOTE_URL" 2>/dev/null || git remote set-url origin "$REMOTE_URL"
fi

echo "OK: full expunge complete for $(basename "$REPO_ROOT") (backup tag: $TAG)"
