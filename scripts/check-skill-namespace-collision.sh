#!/usr/bin/env bash
# check-skill-namespace-collision.sh — shared collision guard for any
# orama-system skill about to be NAMED or PUBLISHED into a namespace shared
# with an external suite. Currently: gstack, which owns ~30 slugs directly
# under ~/.claude/skills/<name>/.
#
# Why this exists: a 2026-07-22 dogfood pass added a skill named "skillify"
# to a global-publish list without checking gstack's own manifest first,
# and silently overwrote gstack's unrelated bundled skillify skill at
# ~/.claude/skills/skillify/SKILL.md. Recovered from gstack's own source
# copy; full incident record: bin/orama-system/skills/skillify/references/
# dogfood-upgrade-log.md. This script is the fix, generalized so the same
# class of bug can't recur anywhere else that names or publishes a skill.
#
# Usage:
#   scripts/check-skill-namespace-collision.sh <slug> [<slug> ...]
#
# Exit 0 if every slug is clear (also prints "clear: <slug>" per slug).
# Exit 1 if ANY slug collides — prints "COLLISION: <slug> — <reason>" to
# stderr for each hit and keeps checking the rest before exiting.
#
# Single source of truth for this check. Callers:
#   - skillify's intake workflow, when a NEW skill is being named (before
#     any write — see skillify/SKILL.md Workflow step 1 and
#     references/modular-skill-authoring.md's Clobber Guard section)
#   - scripts/install-skills.sh's sync_one(), before publishing any skill
#     to ~/.claude/skills/<name>/
# Do not hand-roll a parallel check anywhere else. Extend
# EXTERNAL_SUITE_DIRS / RESERVED_NAMES below instead.
set -euo pipefail

SKILLS_HOME="${HOME:-}/.claude/skills"

# Known external suites that also populate $SKILLS_HOME/<name>/ directly.
# Add a new suite's manifest dir here if one is ever found — do not special-
# case it inline at a call site.
EXTERNAL_SUITE_DIRS=(
  "$SKILLS_HOME/gstack"
)

# This repo's own reserved/sensitive slugs: names that must never be handed
# to a NEW skill or added to a global-publish list under their bare form,
# even when nothing external currently owns them, because reuse would be
# confusing or has already burned us once.
RESERVED_NAMES=(
  gstack   # this repo's own gstack integration skill was literally named
           # "gstack" until 2026-07-22, when it was renamed to
           # gstack-gbrain specifically to stop colliding with gstack's
           # own bundled skill of that name. Never reintroduce this slug.
)

if [ "$#" -eq 0 ]; then
  echo "usage: $0 <slug> [<slug> ...]" >&2
  exit 2
fi

status=0
for slug in "$@"; do
  hit=""
  for suite_dir in "${EXTERNAL_SUITE_DIRS[@]}"; do
    if [ -d "$suite_dir/$slug" ]; then
      hit="external suite already owns this slug at $suite_dir/$slug"
      break
    fi
  done
  if [ -z "$hit" ]; then
    for reserved in "${RESERVED_NAMES[@]}"; do
      if [ "$slug" = "$reserved" ]; then
        hit="reserved name — see RESERVED_NAMES comment in this script"
        break
      fi
    done
  fi
  if [ -n "$hit" ]; then
    echo "COLLISION: '$slug' — $hit" >&2
    status=1
  else
    echo "clear: $slug"
  fi
done
exit "$status"
