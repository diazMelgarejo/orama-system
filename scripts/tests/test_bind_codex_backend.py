import json, os, subprocess, shutil, sys
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


def test_discover_endpoint_accepts_newlines_in_json_filenames(tmp_path):
    d = tmp_path / "codex_apps_server_info"
    d.mkdir()
    shutil.copy(FIX / "server_info_sample.json", d / "server\ninfo.json")
    rc, out, err = _run(f'codex_discover_endpoint "{d}"')
    assert rc == 0, err
    assert out == "http://127.0.0.1:1455", out


def test_models_canary_unreachable_is_nonzero():
    rc, out, _err = _run('codex_models_canary "http://127.0.0.1:0/v1" 1 && echo UP || echo DOWN')
    assert rc == 0
    assert out == "DOWN", out


def test_binder_uses_canonical_workspace_without_stowing_cwd():
    body = BINDER.read_text(encoding="utf-8")
    assert 'WORKSPACE="$OPENCLAW_HOME/.openclaw/agents/codex-agent"' in body
    assert 'AGENT_DIR="$WORKSPACE/agent"' in body
    assert 'agents add codex-agent' in body
    assert 'stow --no-folding -t "$OPENCLAW_HOME" .' not in body


def test_binder_uses_native_codex_auth_without_copying_credential_refs():
    body = BINDER.read_text(encoding="utf-8")
    assert 'openai-codex' in body
    assert 'needs_auth' in body
    assert 'CODEX_API_KEY_REF' not in body
    assert 'models.providers.codex' not in body
    assert 'plugins.allow' in body
    assert 'plugins install openai' in body
    assert 'plugins enable openai' in body
    assert 'needs_plugin' in body


def test_binder_defaults_medium_and_allows_xhigh_opt_in():
    body = BINDER.read_text(encoding="utf-8")
    assert 'EFFORT="medium"' in body
    assert "medium|high|xhigh)" in body


def test_binder_uses_current_agent_schema_and_reconciliation_guards():
    body = BINDER.read_text(encoding="utf-8")
    assert '"codex/gpt-5.5"' in body
    assert 'thinkingDefault' in body
    assert 'tools.profile' in body
    assert 'agents.defaults.subagents.allowAgents' in body
    assert 'current_workspace' in body
    assert 'needs_agent_update' in body
    assert 'config set --batch-json' in body
    assert 'codex serve' not in body
    assert 'openai-completions' not in body


def test_profile_generator_preserves_operator_text_and_converges(tmp_path):
    generator = SKILL / "scripts/generate_codex_openclaw_profile.py"
    workspace = tmp_path / "codex-agent"

    first = subprocess.run(
        [sys.executable, str(generator), "--workspace", str(workspace)],
        capture_output=True,
        check=True,
        text=True,
    )
    assert set(json.loads(first.stdout)["changed"]) == {
        "CODEX.md", "IDENTITY.md", "AGENTS.md", "TOOLS.md", "SECURITY.md"
    }

    codex_md = workspace / "CODEX.md"
    codex_md.write_text(codex_md.read_text(encoding="utf-8") + "\nOperator note.\n", encoding="utf-8")
    security = workspace / "SECURITY.md"
    security.write_text("Operator security policy.\n", encoding="utf-8")

    second = subprocess.run(
        [sys.executable, str(generator), "--workspace", str(workspace)],
        capture_output=True,
        check=True,
        text=True,
    )
    assert json.loads(second.stdout)["changed"] == ["CODEX.md"]

    third = subprocess.run(
        [sys.executable, str(generator), "--workspace", str(workspace)],
        capture_output=True,
        check=True,
        text=True,
    )
    assert json.loads(third.stdout)["changed"] == []
    content = codex_md.read_text(encoding="utf-8")
    assert content.count("<!-- oramaclaw:generated:start -->") == 1
    assert content.count("<!-- oramaclaw:generated:end -->") == 1
    assert "model: codex/gpt-5.5" in content
    assert "Operator note." in content
    assert security.read_text(encoding="utf-8") == "Operator security policy.\n"


def test_profile_generator_rejects_trailing_start_marker(tmp_path):
    generator = SKILL / "scripts/generate_codex_openclaw_profile.py"
    workspace = tmp_path / "codex-agent"
    workspace.mkdir()
    (workspace / "CODEX.md").write_text(
        "<!-- oramaclaw:generated:start -->\nmanaged\n"
        "<!-- oramaclaw:generated:end -->\n"
        "<!-- oramaclaw:generated:start -->\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(generator), "--workspace", str(workspace)],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "duplicate oramaclaw generated marker pairs" in result.stderr
