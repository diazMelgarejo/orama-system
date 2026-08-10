from pathlib import Path

ROOT = Path(__file__).parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def _executable_shell(text: str) -> str:
    """Return non-comment shell lines for behavioral source assertions."""
    return "\n".join(
        line for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


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
    executable = _executable_shell(installer)
    # Documentation may name the retired marker while explaining why it is
    # unsafe. The invariant is that executable installer code never creates or
    # relies on that marker and never invokes Claude's permission bypass.
    assert ".dangerously-skip-accepted" not in executable
    assert "claude --dangerously-skip-permissions" not in executable
    assert "ai-cli-mcp@latest" not in executable
    assert "scripts/ensure_ai_cli_mcp.py" in installer


def test_unix_mcp_optional_argument_arrays_are_bash32_nounset_safe() -> None:
    ensure = _executable_shell(_text("scripts/ensure_requirements.sh"))
    installer = _executable_shell(_text("bin/orama-system/scripts/install-mcp-stack.sh"))

    assert '${MCP_ARGS[@]+"${MCP_ARGS[@]}"}' in ensure
    assert '${_CORE_ARGS[@]+"${_CORE_ARGS[@]}"}' in installer
    assert 'python3 "$MCP_HELPER" "${MCP_ARGS[@]}"' not in ensure
    assert 'python3 "$_READINESS" "${_CORE_ARGS[@]}"' not in installer
    assert "printf ' %q' \"${_CORE_ARGS[@]}\"" not in installer
