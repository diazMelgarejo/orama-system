#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# apply-fork-patches.sh — idempotent, detection-gated fork self-heal (orama)
#
# Re-applies orama's shipped fork fixes to gstack / gbrain after an upgrade
# clobbers them, UNTIL the upstream PRs merge. Fail-closed and transactional:
#
#   • DETECT first   — if the fix is already present (we patched it, OR upstream
#                      merged it), do NOTHING. Marker grep OR `git apply
#                      --reverse --check` (the patch is its own detector).
#   • APPLY safely   — `git apply --check` then apply; on line-drift, `--3way`
#                      merge against blob context. `git apply` is atomic: it
#                      never half-applies. On conflict/drift it warns LOUDLY and
#                      rolls back the patch's files only — never a blind clobber
#                      that could regress other upstream changes.
#   • VERIFY         — run the patch's verify command (e.g. `bun test ...`).
#                      On failure, roll back the touched files. Never leave a
#                      repo half-patched.
#
# Registry-driven: drop `<id>.patch` + `<id>.meta` in patches/ and it is picked
# up. See patches/gstack-1802-staging-guard.{patch,meta}.
#
# Triggered automatically from ~/.zshrc (shell start, --quiet — a no-op when
# already patched) and invocable via the mcp-install skill. Safe to run anytime.
#
# Exit: 0 = all patches present-or-applied-ok; 1 = at least one needs attention.
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

PATCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCHES_DIR="$PATCH_ROOT/patches"

# Target repos (overridable for testing).
GSTACK_ROOT="${GSTACK_ROOT:-$HOME/.claude/skills/gstack}"
GBRAIN_ROOT="${GBRAIN_ROOT:-$HOME/gbrain}"

QUIET=0; DRYRUN=0; rc=0
for a in "$@"; do
  case "$a" in
    --quiet) QUIET=1 ;;
    --dry-run) DRYRUN=1 ;;
    -h|--help) sed -n '2,28p' "${BASH_SOURCE[0]}"; exit 0 ;;
  esac
done

log()  { [ "$QUIET" = 1 ] || printf '%s\n' "$*"; }
warn() { printf '[fork-heal] %s\n' "$*" >&2; }

resolve_target() {  # $1=target keyword → prints repo path or empty
  case "$1" in
    gstack) printf '%s' "$GSTACK_ROOT" ;;
    gbrain) printf '%s' "$GBRAIN_ROOT" ;;
    *) printf '' ;;
  esac
}

# detect_fixed <root> <patch> <markers...> → 0 if fix already present
detect_fixed() {
  local root="$1" patch="$2"; shift 2
  local m
  for m in "$@"; do
    [ -z "$m" ] && continue
    # Marker present anywhere in tracked files ⇒ fixed (covers an upstream merge
    # that reworded our diff but kept the symbol).
    if git -C "$root" grep -q -- "$m" 2>/dev/null; then return 0; fi
  done
  # Or: the patch reverse-applies cleanly ⇒ it is already fully present.
  if git -C "$root" apply --reverse --check "$patch" >/dev/null 2>&1; then return 0; fi
  return 1
}

apply_one() {  # $1 = path to <id>.patch
  local patch="$1" id meta target root verify markers files
  id="$(basename "$patch" .patch)"
  meta="${patch%.patch}.meta"
  [ -f "$meta" ] || { warn "[$id] missing .meta — skipping"; return 1; }
  # shellcheck disable=SC1090
  target=""; verify=""; markers=""
  # shellcheck source=/dev/null
  source "$meta"   # sets: TARGET, VERIFY, MARKERS (space-separated)
  root="$(resolve_target "$TARGET")"

  # Accept both normal checkouts (.git dir) and worktrees (.git gitlink file).
  if [ -z "$root" ] || ! git -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    log "[$id] target '$TARGET' not a git work tree at '$root' — skip"; return 0
  fi

  # shellcheck disable=SC2086
  if detect_fixed "$root" "$patch" $MARKERS; then
    log "[$id] ✓ already present (patched or upstream-merged) — no-op"
    return 0
  fi

  files="$(git -C "$root" apply --numstat "$patch" 2>/dev/null | awk '{print $3}')"

  if [ "$DRYRUN" = 1 ]; then
    if git -C "$root" apply --check "$patch" >/dev/null 2>&1; then
      warn "[$id] WOULD apply cleanly (fix is MISSING — upgrade clobbered it)"
    elif git -C "$root" apply --3way --check "$patch" >/dev/null 2>&1; then
      warn "[$id] WOULD apply via 3-way merge (upstream drifted)"
    else
      warn "[$id] WOULD NOT apply — upstream refactored; manual re-patch needed"
    fi
    return 0
  fi

  warn "[$id] fix MISSING (upgrade clobbered it) — re-applying"
  local applied=0
  if git -C "$root" apply --check "$patch" >/dev/null 2>&1; then
    git -C "$root" apply --whitespace=nowarn "$patch" && applied=1
  elif git -C "$root" apply --3way --whitespace=nowarn "$patch" >/dev/null 2>&1; then
    # --3way can leave conflict markers; treat any conflict as failure.
    if git -C "$root" diff --check >/dev/null 2>&1 && ! grep -rlq '^<<<<<<<' $(printf '%s\n' $files | sed "s|^|$root/|") 2>/dev/null; then
      applied=1
    fi
  fi

  if [ "$applied" != 1 ]; then
    warn "[$id] could NOT apply cleanly (upstream refactored or partially merged PR)."
    warn "[$id] left untouched. Review the PR and re-patch manually if still needed."
    [ -n "$files" ] && (cd "$root" && git checkout -- $files 2>/dev/null || true)
    return 1
  fi

  # Verify — roll back the patch's files on failure (never half-patched).
  if [ -n "${VERIFY:-}" ]; then
    log "[$id] applied — verifying: $VERIFY"
    if ( cd "$root" && eval "$VERIFY" ) >/tmp/fork-heal-$id.log 2>&1; then
      log "[$id] ✓ re-applied + verified"
    else
      warn "[$id] verify FAILED — rolling back (see /tmp/fork-heal-$id.log)"
      [ -n "$files" ] && (cd "$root" && git checkout -- $files 2>/dev/null || true)
      # staging-guard.ts is a NEW file — checkout won't remove it; clean it.
      printf '%s\n' $files | while read -r f; do
        [ -n "$f" ] && ! git -C "$root" ls-files --error-unmatch "$f" >/dev/null 2>&1 && rm -f "$root/$f"
      done
      return 1
    fi
  else
    log "[$id] ✓ re-applied (no verify command)"
  fi
  return 0
}

[ -d "$PATCHES_DIR" ] || { warn "no patches dir at $PATCHES_DIR"; exit 0; }
shopt -s nullglob
found=0
for p in "$PATCHES_DIR"/*.patch; do
  found=1
  apply_one "$p" || rc=1
done
[ "$found" = 0 ] && log "no patches registered"
exit "$rc"
