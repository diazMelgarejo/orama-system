#!/usr/bin/env bash
# consolidate-skills.sh — make a repo's .claude/skills thin read-through wrappers
# over the PERMANENT canonical skills in orama-system/bin/orama-system/, WITHOUT
# losing substance. One canonical source (orama); everything else thin wrappers.
#
# Principles (CIDF / orama-way — additive, non-destructive):
#   * MERGE, never replace/delete/overwrite. Canonical home = the canon base.
#   * only-in-.claude files -> copied into canonical (gained).
#   * in-both identical -> left as-is.
#   * in-both differing -> canonical kept; .claude variant preserved beside it as
#     `<file>.from-claude-<stamp>` AND reported for human harmonization.
#   * each .claude SKILL.md backed up to `SKILL.md.premerge-<stamp>.bak` before it
#     becomes a thin wrapper.
#   * --wrapper-only: skip the merge (use when canon is already the verified
#     superset, e.g. a legacy duplicate repo pointing at orama).
#   * Idempotent: a SKILL.md already carrying the wrapper marker is skipped.
#
# Usage:
#   consolidate-skills.sh [--apply] [--stamp YYYYmmdd] \
#     [--skills-dir DIR] [--canon-base DIR] [--bundle-name NAME] [--wrapper-only]
#   Defaults target this repo (orama-system) -> its own bin/orama-system.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"               # orama-system repo root
APPLY=0; STAMP=""; WRAPPER_ONLY=0
SKILLS_DIR="$ROOT/.claude/skills"
CANON_BASE="$ROOT/bin/orama-system"
BUNDLE_NAME="orama-system"                              # skill name that maps to CANON_BASE itself
while [ $# -gt 0 ]; do
  case "$1" in
    --apply) APPLY=1 ;;
    --wrapper-only) WRAPPER_ONLY=1 ;;
    --stamp) STAMP="${2:-}"; shift ;;
    --stamp=*) STAMP="${1#--stamp=}" ;;
    --skills-dir) SKILLS_DIR="${2:-}"; shift ;;
    --canon-base) CANON_BASE="${2:-}"; shift ;;
    --bundle-name) BUNDLE_NAME="${2:-}"; shift ;;
  esac
  shift
done
[ -n "$STAMP" ] || STAMP="$(date +%Y%m%d 2>/dev/null || echo manual)"

WRAP_MARKER="<!-- THIN-WRAPPER: canonical skill lives in orama-system/bin/orama-system -->"
say(){ printf '%s\n' "$*"; }

[ -d "$SKILLS_DIR" ] || { say "[consolidate-skills] no $SKILLS_DIR — nothing to do"; exit 0; }
say "[consolidate-skills] mode=$([ "$APPLY" = 1 ] && echo APPLY || echo DRY-RUN) wrapper_only=$WRAPPER_ONLY stamp=$STAMP"
say "[consolidate-skills] skills: $SKILLS_DIR"
say "[consolidate-skills] canon:  $CANON_BASE (bundle=$BUNDLE_NAME)"

for d in "$SKILLS_DIR"/*/; do
  [ -d "$d" ] || continue
  name="$(basename "$d")"
  if [ "$name" = "$BUNDLE_NAME" ]; then canon="$CANON_BASE"; else canon="$CANON_BASE/skills/$name"; fi
  say ""; say "── skill: $name  ->  canonical $canon"

  if [ -f "$d/SKILL.md" ] && grep -qF "$WRAP_MARKER" "$d/SKILL.md" 2>/dev/null; then
    say "   already a thin wrapper — skip"; continue
  fi

  if [ "$WRAPPER_ONLY" = 0 ]; then
    [ "$APPLY" = 1 ] && mkdir -p "$canon"
    while IFS= read -r -d '' f; do
      rel="${f#$d}"; tgt="$canon/$rel"
      if [ ! -e "$tgt" ]; then
        say "   + gain: $rel"
        [ "$APPLY" = 1 ] && { mkdir -p "$(dirname "$tgt")"; cp -p "$f" "$tgt"; }
      elif ! cmp -s "$f" "$tgt"; then
        say "   ! DIFFERS (canon kept; variant preserved): $rel"
        [ "$APPLY" = 1 ] && cp -p "$f" "$tgt.from-claude-$STAMP"
      fi
    done < <(find "$d" -type f ! -name '*.premerge-*.bak' -print0)
  else
    [ -d "$canon" ] && say "   wrapper-only: canon exists, skipping merge" || say "   WARN: canon missing ($canon) — wrapper would dangle"
  fi

  if [ -f "$d/SKILL.md" ]; then
    fm="$(awk 'NR==1&&/^---/{p=1} p{print} p&&NR>1&&/^---/{exit}' "$d/SKILL.md" 2>/dev/null)"
    rel_canon="$(python3 -c "import os;print(os.path.relpath('$canon','$d'))" 2>/dev/null || echo "$canon")"
    say "   ~ backup SKILL.md -> SKILL.md.premerge-$STAMP.bak; wrapper -> $rel_canon"
    if [ "$APPLY" = 1 ]; then
      cp -p "$d/SKILL.md" "$d/SKILL.md.premerge-$STAMP.bak"
      {
        [ -n "$fm" ] && printf '%s\n\n' "$fm" || printf -- '---\nname: %s\n---\n\n' "$name"
        printf '%s\n\n' "$WRAP_MARKER"
        printf '# %s (thin wrapper)\n\n' "$name"
        printf 'Canonical, permanent implementation: `%s/`.\n' "$rel_canon"
        printf '**Read it before proceeding** — this wrapper only carries discovery metadata.\n\n'
        printf 'Pre-wrapper body preserved at `SKILL.md.premerge-%s.bak`.\n' "$STAMP"
      } > "$d/SKILL.md"
    fi
  fi
done
say ""; say "[consolidate-skills] done (nothing overwritten/deleted)."
