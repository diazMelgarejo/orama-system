#!/usr/bin/env bash
# Smoke test: run_agent_security_scans.sh must exit non-zero when a scanner
# fails, and the usage error path must exit 2. Regression test for the
# "exit $FAIL propagation" finding on PR #321 -- exercises the real script,
# not a reimplementation of it.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/run_agent_security_scans.sh"
FAKE_BIN="$(mktemp -d)"
trap 'rm -rf "$FAKE_BIN"' EXIT

fail=0
assert_exit() {
  local desc="$1" expected="$2"; shift 2
  local actual=0
  "$@" >/dev/null 2>&1
  actual=$?
  if [[ "$actual" -eq "$expected" ]]; then
    echo "[test] OK: $desc (exit $actual)"
  else
    echo "[test] FAIL: $desc (expected exit $expected, got $actual)"
    fail=1
  fi
}

# Unknown tool argument: usage error, exit 2, independent of FAIL.
assert_exit "unknown tool arg exits 2" 2 bash "$SCRIPT" not-a-real-tool

# Stub `aguara` on PATH so scan_aguara() skips the go-install branch
# entirely and calls our stub directly. A stub that always exits 1 makes
# `run "aguara:$path" aguara ...` set FAIL=1 -- proving that failure
# actually reaches the script's own final `exit "$FAIL"`, not just an
# internal function's return value.
cat >"$FAKE_BIN/aguara" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
chmod +x "$FAKE_BIN/aguara"
assert_exit "a failing scanner propagates to the script's final exit code" 1 \
  env PATH="$FAKE_BIN:$PATH" bash "$SCRIPT" aguara

# scan_ramparts() sets FAIL=1 (not exit 1 directly) when GITHUB_ACTIONS is
# set and neither `ramparts` nor `cargo` is on PATH -- this only exercises
# the aguara branch above, so a regression that dropped the ramparts FAIL=1
# assignment could still pass without this. Use /usr/bin:/bin (real core
# utils bash/env/etc. still resolve) rather than an empty PATH.
assert_exit "missing ramparts fails in CI" 1 \
  env GITHUB_ACTIONS=1 PATH="/usr/bin:/bin" bash "$SCRIPT" ramparts

exit "$fail"
