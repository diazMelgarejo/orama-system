#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Protocol

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "scripts" / "review" / "verify_trusted_install.py"


class TrustedInstallModule(Protocol):
    def resolve_repo_root(self) -> Path: ...
    def trusted_install_allowed(self, root: Path) -> tuple[bool, str]: ...
    def verify_commit_signature(self, root: Path, ref: str) -> tuple[bool, str]: ...
    def main(self) -> int: ...

    def _git(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]: ...


@pytest.fixture
def trusted_mod(monkeypatch: pytest.MonkeyPatch) -> TrustedInstallModule:
    spec = importlib.util.spec_from_file_location("verify_trusted_install", VERIFY)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module  # type: ignore[return-value]


def test_trusted_install_allows_override(
    trusted_mod: TrustedInstallModule, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ORAMA_TRUST_HERMES_SYNC", "1")
    monkeypatch.delenv("ORAMA_SKIP_HERMES_SYNC", raising=False)
    ok, reason = trusted_mod.trusted_install_allowed(trusted_mod.resolve_repo_root())
    assert ok is True
    assert "override" in reason


def test_trusted_install_blocks_skip(
    trusted_mod: TrustedInstallModule, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ORAMA_SKIP_HERMES_SYNC", "1")
    monkeypatch.delenv("ORAMA_TRUST_HERMES_SYNC", raising=False)
    ok, reason = trusted_mod.trusted_install_allowed(trusted_mod.resolve_repo_root())
    assert ok is False
    assert "SKIP" in reason


def test_verify_commit_signature_skipped_by_default(
    trusted_mod: TrustedInstallModule, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ORAMA_VERIFY_COMMIT_SIG", raising=False)
    ok, reason = trusted_mod.verify_commit_signature(Path("."), "deadbeef")
    assert ok is True
    assert "skipped" in reason


def test_verify_commit_signature_requires_allowed_fingerprints(
    trusted_mod: TrustedInstallModule, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ORAMA_VERIFY_COMMIT_SIG", "1")
    monkeypatch.delenv("ORAMA_ALLOWED_GPG_FINGERPRINTS", raising=False)
    ok, reason = trusted_mod.verify_commit_signature(trusted_mod.resolve_repo_root(), "HEAD")
    assert ok is False
    assert "ORAMA_ALLOWED_GPG_FINGERPRINTS" in reason


def test_verify_commit_signature_uses_supported_git_invocation(
    trusted_mod: TrustedInstallModule, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:1] == ("verify-commit",):
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[:2] == ("show", "-s"):
            return subprocess.CompletedProcess(args, 0, "ABCD1234EF567890", "")
        return subprocess.CompletedProcess(args, 1, "", "missing ref")

    monkeypatch.setenv("ORAMA_VERIFY_COMMIT_SIG", "1")
    monkeypatch.setenv("ORAMA_ALLOWED_GPG_FINGERPRINTS", "ABCD1234EF567890")
    monkeypatch.setattr(trusted_mod, "_git", fake_git)

    ok, reason = trusted_mod.verify_commit_signature(Path("/tmp"), "deadbeef")
    assert ok is True
    assert "allowed signer" in reason
    assert ("verify-commit", "deadbeef") in calls
    assert all("-q" not in call for call in calls)


def test_verify_commit_signature_rejects_unapproved_signer(
    trusted_mod: TrustedInstallModule, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        if args[:1] == ("verify-commit",):
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[:2] == ("show", "-s"):
            return subprocess.CompletedProcess(args, 0, "ZZZZ9999", "")
        return subprocess.CompletedProcess(args, 1, "", "")

    monkeypatch.setenv("ORAMA_VERIFY_COMMIT_SIG", "1")
    monkeypatch.setenv("ORAMA_ALLOWED_GPG_FINGERPRINTS", "ABCD1234")
    monkeypatch.setattr(trusted_mod, "_git", fake_git)

    ok, reason = trusted_mod.verify_commit_signature(Path("/tmp"), "deadbeef")
    assert ok is False
    assert "not in ORAMA_ALLOWED_GPG_FINGERPRINTS" in reason


def test_main_logs_public_status_to_stdout(
    trusted_mod: TrustedInstallModule,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("ORAMA_SKIP_HERMES_SYNC", raising=False)
    monkeypatch.setenv("ORAMA_TRUST_HERMES_SYNC", "1")
    monkeypatch.setattr(sys, "argv", ["verify_trusted_install.py"])
    assert trusted_mod.main() == 0
    assert "trusted install check passed" in capsys.readouterr().out
