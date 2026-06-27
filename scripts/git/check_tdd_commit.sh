#!/usr/bin/env bash
# TDD gate for web/src/ — requires a staged *.test.ts(x) when production TS/TSX
# changes are staged, unless the commit message documents tdd-skip: <reason>.
# Canonical policy: docs/TDD.md. Wired from .githooks/commit-msg.
set -euo pipefail

msg_file="${1:-}"

if [[ -n "$msg_file" && -f "$msg_file" ]]; then
  if grep -qE '(^|[[:space:]])tdd-skip:' "$msg_file"; then
    exit 0
  fi
fi

staged=()
while IFS= read -r line; do
  staged+=("$line")
done < <(git diff --cached --name-only --diff-filter=ACMRT 2>/dev/null || true)

prod=()
tests=()
for f in "${staged[@]}"; do
  [[ "$f" == web/src/* ]] || continue
  case "$f" in
    web/src/test/*) continue ;;
    *.test.ts|*.test.tsx) tests+=("$f"); continue ;;
    *.ts|*.tsx) prod+=("$f");;
  esac
done

if ((${#prod[@]} == 0)); then
  exit 0
fi

if ((${#tests[@]} > 0)); then
  exit 0
fi

echo "ERROR: TDD gate — web/src/ production file(s) staged without accompanying *.test.ts(x)." >&2
printf '  %s\n' "${prod[@]}" >&2
echo "Add a test in the same commit, or document tdd-skip: <reason> in the commit message (docs/TDD.md)." >&2
exit 1
