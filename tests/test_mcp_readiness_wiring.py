from pathlib import Path

ROOT = Path(__file__).parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def test_unix_launcher_delegates_to_requirement_gate() -> None:
    start = _text("start.sh")
    ensure = _text("scripts/ensure_requirements.sh")
    assert 'scripts/ensure_requirements.sh' in start
    assert 'scripts/ensure_ai_cli_mcp.py' in ensure


def test_windows_launcher_reaches_shared_gate_through_partner_cli_hook() -> None:
    start = _text("platform/windows/start.ps1")
    partner = _text("platform/windows/ensure-partner-cli-paths.ps1")
    ensure = _text("scripts/ensure_requirements.ps1")
    assert 'ensure-partner-cli-paths.ps1' in start
    assert 'scripts\\ensure_ai_cli_mcp.py' in partner
    assert 'scripts\\ensure_ai_cli_mcp.py' in ensure


def test_windows_requirement_gate_remains_powershell_51_compatible() -> None:
    ensure = _text("scripts/ensure_requirements.ps1")
    assert "??" not in ensure


def test_installer_never_synthesizes_provider_consent() -> None:
    installer = _text("bin/orama-system/scripts/install-mcp-stack.sh")
    assert ".dangerously-skip-accepted" not in installer
    assert "claude --dangerously-skip-permissions" not in installer
    assert "ai-cli-mcp@latest" not in installer
    assert "scripts/ensure_ai_cli_mcp.py" in installer
