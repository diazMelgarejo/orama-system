"""Tests for verify_partner_canaries.py — the hermes-harness partner canary checker.

Covers: Status enum, Result dataclass, _run() helper, each check_*() function,
and main() CLI behaviour (skip flags, JSON output, exit code).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
CANARY_SCRIPT = (
    ROOT
    / "bin"
    / "orama-system"
    / "skills"
    / "hermes-harness"
    / "scripts"
    / "verify_partner_canaries.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("verify_partner_canaries", CANARY_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Register in sys.modules before exec so @dataclass can resolve __module__
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def vc():
    return _load_module()


# ── Status enum ───────────────────────────────────────────────────────────────

def test_status_values(vc):
    assert vc.Status.PASS.value == "PASS"
    assert vc.Status.FAIL.value == "FAIL"
    assert vc.Status.UNAVAILABLE.value == "UNAVAILABLE"
    assert vc.Status.SKIPPED.value == "SKIPPED"


def test_status_is_str_subclass(vc):
    assert isinstance(vc.Status.PASS, str)


# ── Result dataclass ──────────────────────────────────────────────────────────

def test_result_defaults(vc):
    r = vc.Result("LM Studio /v1/models", vc.Status.PASS)
    assert r.name == "LM Studio /v1/models"
    assert r.status == vc.Status.PASS
    assert r.detail == ""
    assert r.required is True


def test_result_optional_not_required(vc):
    r = vc.Result("AGY", vc.Status.UNAVAILABLE, "agy not on PATH", required=False)
    assert r.required is False


# ── _run helper ───────────────────────────────────────────────────────────────

def test_run_captures_stdout_stderr(vc, tmp_path):
    rc, out, err = vc._run([sys.executable, "-c", "import sys; print('hello'); print('err', file=sys.stderr)"])
    assert rc == 0
    assert out == "hello"
    assert err == "err"


def test_run_nonzero_returncode(vc):
    rc, _out, _err = vc._run([sys.executable, "-c", "import sys; sys.exit(42)"])
    assert rc == 42


def test_run_timeout_returns_minus_one(vc):
    rc, out, err = vc._run([sys.executable, "-c", "import time; time.sleep(60)"], timeout=1)
    assert rc == -1
    assert out == ""
    assert err == "timed out"


def test_run_file_not_found_returns_minus_two(vc):
    rc, out, err = vc._run(["no-such-binary-abc123"])
    assert rc == -2
    assert out == ""
    assert "'no-such-binary-abc123' not found on PATH" in err


def test_run_strips_whitespace(vc):
    _rc, out, _err = vc._run([sys.executable, "-c", "print('  hello  ')"])
    assert out == "hello"


# ── check_lm_studio ───────────────────────────────────────────────────────────

class _MockResponse:
    """Minimal urllib response mock."""
    def __init__(self, data: dict):
        self._data = json.dumps(data).encode()

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


def test_check_lm_studio_pass(vc):
    models_payload = {"data": [{"id": "model-a"}, {"id": "model-b"}]}
    completion_payload = {"choices": [{"message": {"content": "LM_READY"}}]}
    with patch("urllib.request.urlopen", side_effect=[
        _MockResponse(models_payload),
        _MockResponse(completion_payload),
    ]):
        result = vc.check_lm_studio("http://localhost:1234/v1", timeout=5)
    assert result.status == vc.Status.PASS
    assert "2 model(s)" in result.detail


def test_check_lm_studio_fail_missing_marker(vc):
    models_payload = {"data": [{"id": "model-a"}]}
    completion_payload = {"choices": [{"message": {"content": "Hello there!"}}]}
    with patch("urllib.request.urlopen", side_effect=[
        _MockResponse(models_payload),
        _MockResponse(completion_payload),
    ]):
        result = vc.check_lm_studio("http://localhost:1234/v1", timeout=5)
    assert result.status == vc.Status.FAIL
    assert "readiness marker missing" in result.detail


def test_check_lm_studio_fail_zero_models(vc):
    payload = {"data": []}
    with patch("urllib.request.urlopen", return_value=_MockResponse(payload)):
        result = vc.check_lm_studio("http://localhost:1234/v1", timeout=5)
    assert result.status == vc.Status.FAIL
    assert "no models loaded" in result.detail


def test_check_lm_studio_url_normalisation_no_double_v1(vc):
    """base_url already ending in /v1 must not produce /v1/v1/models."""
    captured_url = []

    import urllib.error

    def fake_urlopen(url, timeout):
        captured_url.append(url)
        raise urllib.error.URLError("connection refused")

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        vc.check_lm_studio("http://localhost:1234/v1", timeout=1)

    assert captured_url[0].endswith("/v1/models"), captured_url[0]
    assert "/v1/v1/" not in captured_url[0]


def test_check_lm_studio_url_no_trailing_v1(vc):
    """base_url without /v1 must still produce the correct /v1/models path."""
    captured_url = []

    import urllib.error

    def fake_urlopen(url, timeout):
        captured_url.append(url)
        raise urllib.error.URLError("connection refused")

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        vc.check_lm_studio("http://localhost:1234", timeout=1)

    assert captured_url[0] == "http://localhost:1234/v1/models"


def test_check_lm_studio_fail_on_url_error(vc):
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        result = vc.check_lm_studio("http://localhost:1234/v1", timeout=1)
    assert result.status == vc.Status.FAIL
    assert result.name == "LM Studio"
    assert result.required is True


def test_check_lm_studio_fail_on_generic_exception(vc):
    with patch("urllib.request.urlopen", side_effect=OSError("network unreachable")):
        result = vc.check_lm_studio("http://localhost:1234/v1", timeout=1)
    assert result.status == vc.Status.FAIL


# ── check_hermes ──────────────────────────────────────────────────────────────

def test_check_hermes_unavailable_when_not_on_path(vc):
    with patch("shutil.which", return_value=None):
        result = vc.check_hermes(timeout=5)
    assert result.status == vc.Status.UNAVAILABLE
    assert result.required is True
    assert "hermes not on PATH" in result.detail


def test_check_hermes_pass_when_ready_string_present(vc):
    with patch("shutil.which", return_value="hermes"):
        with patch.object(vc, "_run", return_value=(0, "HERMES_READY", "")):
            result = vc.check_hermes(timeout=15)
    assert result.status == vc.Status.PASS
    assert "HERMES_READY" in result.detail


def test_check_hermes_fail_when_ready_string_missing(vc):
    with patch("shutil.which", return_value="hermes"):
        with patch.object(vc, "_run", return_value=(0, "something else", "")):
            result = vc.check_hermes(timeout=15)
    assert result.status == vc.Status.FAIL
    assert result.required is True


def test_check_hermes_fail_on_nonzero_returncode(vc):
    with patch("shutil.which", return_value="hermes"):
        with patch.object(vc, "_run", return_value=(1, "", "provider error")):
            result = vc.check_hermes(timeout=15)
    assert result.status == vc.Status.FAIL


def test_check_hermes_unavailable_on_minus_two(vc):
    """rc=-2 means the binary wasn't found by subprocess (PATH mismatch)."""
    with patch("shutil.which", return_value="hermes"):
        with patch.object(vc, "_run", return_value=(-2, "", "hermes not found")):
            result = vc.check_hermes(timeout=15)
    assert result.status == vc.Status.UNAVAILABLE


def test_check_hermes_fail_on_timeout(vc):
    with patch("shutil.which", return_value="hermes"):
        with patch.object(vc, "_run", return_value=(-1, "", "timed out")):
            result = vc.check_hermes(timeout=15)
    assert result.status == vc.Status.FAIL


# ── check_agy ────────────────────────────────────────────────────────────────

def test_check_agy_unavailable_when_not_on_path(vc):
    with patch("shutil.which", return_value=None):
        result = vc.check_agy(timeout=5)
    assert result.status == vc.Status.UNAVAILABLE
    assert result.required is False


def test_check_agy_pass_when_ready_string_present(vc):
    with patch("shutil.which", return_value="agy"):
        with patch.object(vc, "_run", return_value=(0, "AGY_READY", "")):
            result = vc.check_agy(timeout=10)
    assert result.status == vc.Status.PASS
    assert result.required is False


def test_check_agy_unavailable_on_empty_stdout_rc0(vc):
    """rc=0 with empty stdout means quota exhausted — should be UNAVAILABLE not FAIL."""
    with patch("shutil.which", return_value="agy"):
        with patch.object(vc, "_run", return_value=(0, "", "")):
            result = vc.check_agy(timeout=10)
    assert result.status == vc.Status.UNAVAILABLE
    assert "quota" in result.detail.lower()


def test_check_agy_fail_on_nonzero_returncode(vc):
    with patch("shutil.which", return_value="agy"):
        with patch.object(vc, "_run", return_value=(1, "", "error")):
            result = vc.check_agy(timeout=10)
    assert result.status == vc.Status.FAIL


def test_check_agy_unavailable_on_minus_two(vc):
    with patch("shutil.which", return_value="agy"):
        with patch.object(vc, "_run", return_value=(-2, "", "agy not found")):
            result = vc.check_agy(timeout=10)
    assert result.status == vc.Status.UNAVAILABLE


def test_check_agy_fail_output_does_not_contain_ready(vc):
    """Output present but missing AGY_READY → FAIL, not UNAVAILABLE."""
    with patch("shutil.which", return_value="agy"):
        with patch.object(vc, "_run", return_value=(0, "something else", "")):
            result = vc.check_agy(timeout=10)
    assert result.status == vc.Status.FAIL


# ── check_codex ───────────────────────────────────────────────────────────────

def test_check_codex_unavailable_when_not_on_path(vc):
    with patch("shutil.which", return_value=None):
        result = vc.check_codex(timeout=5)
    assert result.status == vc.Status.UNAVAILABLE
    assert result.required is False


def test_check_codex_pass_when_version_present(vc):
    with patch("shutil.which", return_value="codex"):
        with patch.object(vc, "_run", return_value=(0, "codex-cli 1.2.3", "")):
            result = vc.check_codex(timeout=5)
    assert result.status == vc.Status.PASS
    assert "codex-cli 1.2.3" in result.detail


def test_check_codex_uses_first_line_of_version(vc):
    with patch("shutil.which", return_value="codex"):
        with patch.object(vc, "_run", return_value=(0, "codex-cli 1.2.3\nother line", "")):
            result = vc.check_codex(timeout=5)
    assert result.detail == "codex-cli 1.2.3"


def test_check_codex_fail_on_nonzero_rc(vc):
    with patch("shutil.which", return_value="codex"):
        with patch.object(vc, "_run", return_value=(1, "", "")):
            result = vc.check_codex(timeout=5)
    assert result.status == vc.Status.FAIL


def test_check_codex_fail_when_rc0_but_empty_output(vc):
    with patch("shutil.which", return_value="codex"):
        with patch.object(vc, "_run", return_value=(0, "", "")):
            result = vc.check_codex(timeout=5)
    assert result.status == vc.Status.FAIL


# ── main() — skip flags and exit code ─────────────────────────────────────────

def _mock_check_pass(vc, name, required=True):
    return vc.Result(name, vc.Status.PASS, "ok", required=required)


def _mock_check_fail(vc, name, required=True):
    return vc.Result(name, vc.Status.FAIL, "failed", required=required)


def test_main_returns_0_when_all_required_pass(vc, monkeypatch):
    lm_pass = vc.Result("LM Studio /v1/models", vc.Status.PASS, "1 model(s) listed")
    hermes_pass = vc.Result("Hermes", vc.Status.PASS, "HERMES_READY received")
    monkeypatch.setattr(vc, "check_lm_studio", lambda url, timeout: lm_pass)
    monkeypatch.setattr(vc, "check_hermes", lambda timeout: hermes_pass)
    monkeypatch.setattr(vc, "check_agy", lambda timeout: vc.Result("AGY", vc.Status.UNAVAILABLE, "", required=False))
    monkeypatch.setattr(vc, "check_codex", lambda timeout: vc.Result("Codex", vc.Status.UNAVAILABLE, "", required=False))

    old_argv = sys.argv
    sys.argv = ["verify_partner_canaries.py"]
    try:
        rc = vc.main()
    finally:
        sys.argv = old_argv
    assert rc == 0


def test_main_returns_1_when_required_canary_fails(vc, monkeypatch):
    lm_fail = vc.Result("LM Studio /v1/models", vc.Status.FAIL, "connection refused")
    monkeypatch.setattr(vc, "check_lm_studio", lambda url, timeout: lm_fail)
    monkeypatch.setattr(vc, "check_hermes", lambda timeout: vc.Result("Hermes", vc.Status.SKIPPED, "--skip-hermes"))
    monkeypatch.setattr(vc, "check_agy", lambda timeout: vc.Result("AGY", vc.Status.SKIPPED, "--skip-agy", required=False))
    monkeypatch.setattr(vc, "check_codex", lambda timeout: vc.Result("Codex", vc.Status.SKIPPED, "--skip-codex", required=False))

    old_argv = sys.argv
    sys.argv = ["verify_partner_canaries.py", "--skip-hermes", "--skip-agy", "--skip-codex"]
    try:
        rc = vc.main()
    finally:
        sys.argv = old_argv
    assert rc == 1


def test_main_json_output(vc, monkeypatch, capsys):
    lm_pass = vc.Result("LM Studio /v1/models", vc.Status.PASS, "2 model(s) listed")
    monkeypatch.setattr(vc, "check_lm_studio", lambda url, timeout: lm_pass)
    monkeypatch.setattr(vc, "check_hermes", lambda timeout: vc.Result("Hermes", vc.Status.SKIPPED, "--skip-hermes"))
    monkeypatch.setattr(vc, "check_agy", lambda timeout: vc.Result("AGY", vc.Status.SKIPPED, "", required=False))
    monkeypatch.setattr(vc, "check_codex", lambda timeout: vc.Result("Codex", vc.Status.SKIPPED, "", required=False))

    old_argv = sys.argv
    sys.argv = ["verify_partner_canaries.py", "--skip-hermes", "--skip-agy", "--skip-codex", "--json"]
    try:
        vc.main()
    finally:
        sys.argv = old_argv

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "canaries" in data
    assert isinstance(data["canaries"], list)
    names = [c["name"] for c in data["canaries"]]
    assert "LM Studio /v1/models" in names


def test_main_skip_hermes_inserts_skipped_result(vc, monkeypatch):
    lm_pass = vc.Result("LM Studio /v1/models", vc.Status.PASS, "1 model(s) listed")
    monkeypatch.setattr(vc, "check_lm_studio", lambda url, timeout: lm_pass)
    monkeypatch.setattr(vc, "check_agy", lambda timeout: vc.Result("AGY", vc.Status.SKIPPED, "", required=False))
    monkeypatch.setattr(vc, "check_codex", lambda timeout: vc.Result("Codex", vc.Status.SKIPPED, "", required=False))

    old_argv = sys.argv
    sys.argv = ["verify_partner_canaries.py", "--skip-hermes", "--skip-agy", "--skip-codex"]
    try:
        rc = vc.main()
    finally:
        sys.argv = old_argv

    # Skipped required canary must NOT count as a failure
    assert rc == 0


def test_main_unavailable_required_counts_as_failure(vc, monkeypatch):
    lm_pass = vc.Result("LM Studio /v1/models", vc.Status.PASS, "1 model(s) listed")
    hermes_unavail = vc.Result("Hermes", vc.Status.UNAVAILABLE, "hermes not on PATH", required=True)
    monkeypatch.setattr(vc, "check_lm_studio", lambda url, timeout: lm_pass)
    monkeypatch.setattr(vc, "check_hermes", lambda timeout: hermes_unavail)
    monkeypatch.setattr(vc, "check_agy", lambda timeout: vc.Result("AGY", vc.Status.UNAVAILABLE, "", required=False))
    monkeypatch.setattr(vc, "check_codex", lambda timeout: vc.Result("Codex", vc.Status.UNAVAILABLE, "", required=False))

    old_argv = sys.argv
    sys.argv = ["verify_partner_canaries.py"]
    try:
        rc = vc.main()
    finally:
        sys.argv = old_argv
    assert rc == 1


def test_main_optional_failure_does_not_fail_run(vc, monkeypatch):
    """AGY FAIL (optional) with all required passing → return 0."""
    lm_pass = vc.Result("LM Studio /v1/models", vc.Status.PASS, "1 model(s) listed")
    hermes_pass = vc.Result("Hermes", vc.Status.PASS, "HERMES_READY received")
    agy_fail = vc.Result("AGY", vc.Status.FAIL, "rc=1", required=False)
    codex_unavail = vc.Result("Codex", vc.Status.UNAVAILABLE, "codex not on PATH", required=False)
    monkeypatch.setattr(vc, "check_lm_studio", lambda url, timeout: lm_pass)
    monkeypatch.setattr(vc, "check_hermes", lambda timeout: hermes_pass)
    monkeypatch.setattr(vc, "check_agy", lambda timeout: agy_fail)
    monkeypatch.setattr(vc, "check_codex", lambda timeout: codex_unavail)

    old_argv = sys.argv
    sys.argv = ["verify_partner_canaries.py"]
    try:
        rc = vc.main()
    finally:
        sys.argv = old_argv
    assert rc == 0


def test_main_json_has_required_field_per_entry(vc, monkeypatch, capsys):
    lm_pass = vc.Result("LM Studio /v1/models", vc.Status.PASS, "1 model(s) listed")
    monkeypatch.setattr(vc, "check_lm_studio", lambda url, timeout: lm_pass)
    monkeypatch.setattr(vc, "check_hermes", lambda timeout: vc.Result("Hermes", vc.Status.SKIPPED, "", required=True))
    monkeypatch.setattr(vc, "check_agy", lambda timeout: vc.Result("AGY", vc.Status.SKIPPED, "", required=False))
    monkeypatch.setattr(vc, "check_codex", lambda timeout: vc.Result("Codex", vc.Status.SKIPPED, "", required=False))

    old_argv = sys.argv
    sys.argv = ["verify_partner_canaries.py", "--skip-hermes", "--skip-agy", "--skip-codex", "--json"]
    try:
        vc.main()
    finally:
        sys.argv = old_argv

    data = json.loads(capsys.readouterr().out)
    for entry in data["canaries"]:
        assert "required" in entry
        assert "status" in entry
        assert "name" in entry
        assert "detail" in entry