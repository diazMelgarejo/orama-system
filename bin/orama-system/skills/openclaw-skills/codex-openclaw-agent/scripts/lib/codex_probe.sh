#!/usr/bin/env bash
# codex_probe.sh — Stage 0 probe helpers for bind_codex_backend.sh.
# Evidence-only: NO mutation, NO secret values printed (references only).
# PT-MM3: trust live canaries over stale ~/.codex state files.

# Discover the Codex app-server base_url from the per-session server-info dir
# (~/.codex/cache/codex_apps_server_info/<hash>.json). Echoes the newest base_url.
codex_discover_endpoint() {
  local dir="${1:-$HOME/.codex/cache/codex_apps_server_info}"
  [ -d "$dir" ] || return 1
  python3 - "$dir" <<'PY'
import json
from pathlib import Path
import sys

try:
    directory = Path(sys.argv[1])
    newest = max(
        (path for path in directory.glob("*.json") if path.is_file()),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
    )
    d = json.loads(newest.read_text(encoding="utf-8"))
except (OSError, ValueError, json.JSONDecodeError):
    sys.exit(1)
url = d.get("base_url") or d.get("baseUrl") or ""
if not url:
    sys.exit(1)
print(url.rstrip("/"))
PY
}

# PT-MM2 canary: confirm the discovered endpoint actually serves the
# OpenAI-compatible /v1/models route. Uses curl (system CAs). 0 = reachable.
codex_models_canary() {
  local endpoint="$1" timeout="${2:-5}"
  [ -n "$endpoint" ] || return 1
  local code
  code="$(curl -s -o /dev/null -m "$timeout" -w '%{http_code}' "$endpoint/models" 2>/dev/null)"
  case "$code" in 200|401|403) return 0 ;; *) return 1 ;; esac
}
