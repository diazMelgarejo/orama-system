import json, os, subprocess, shutil, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / "bin/orama-system/skills/openclaw-skills/codex-openclaw-agent"
PROBE_LIB = SKILL / "scripts/lib/codex_probe.sh"
BINDER = SKILL / "scripts/bind_codex_backend.sh"
FIX = Path(__file__).parent / "fixtures/codex"


def _run(snippet: str, env=None):
    """Source the probe lib and run a snippet; return (rc, stdout, stderr)."""
    full = f'set -e; source "{PROBE_LIB}"; {snippet}'
    p = subprocess.run(["bash", "-c", full], capture_output=True, text=True,
                       env={**os.environ, **(env or {})})
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def test_discover_endpoint_from_server_info_dir(tmp_path):
    d = tmp_path / "codex_apps_server_info"
    d.mkdir()
    shutil.copy(FIX / "server_info_sample.json", d / "abc123.json")
    rc, out, err = _run(f'codex_discover_endpoint "{d}"')
    assert rc == 0, err
    assert out == "http://127.0.0.1:1455", out


def test_models_canary_unreachable_is_nonzero():
    rc, out, err = _run('codex_models_canary "http://127.0.0.1:59999/v1" 1 && echo UP || echo DOWN')
    assert rc == 0
    assert out == "DOWN", out


def test_binder_writes_runtime_agent_dir_without_stowing_cwd():
    body = BINDER.read_text(encoding="utf-8")
    assert 'AGENT_DIR="$OPENCLAW_HOME/.openclaw/agents/codex-agent"' in body
    assert 'stow --no-folding -t "$OPENCLAW_HOME" .' not in body


def test_binder_accepts_codex_auth_json_or_api_key_env_refs():
    body = BINDER.read_text(encoding="utf-8")
    assert 'CODEX_API_KEY' in body
    assert 'OPENAI_API_KEY' in body
    assert '$HOME/.codex/auth.json' in body


def test_binder_defaults_medium_and_allows_xhigh_opt_in():
    body = BINDER.read_text(encoding="utf-8")
    assert 'EFFORT="${EFFORT:-medium}"' in body
    assert "[--effort medium|high|xhigh]" in body
    assert "medium|high|xhigh)" in body


def test_binder_uses_real_codex_supervisor_plugin_name():
    body = BINDER.read_text(encoding="utf-8")
    assert "codex-supervisor" in body
    assert "openclaw-codex-app-server" not in body
