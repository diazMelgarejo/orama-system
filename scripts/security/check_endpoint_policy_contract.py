#!/usr/bin/env python3
"""Validate orama-system's endpoint transport policy peer contract.

Perpetua-Tools owns the Python transport reconstruction implementation. This
checker keeps orama-system wired to the same contract so generated configs,
skills, and orchestration guidance do not drift from the canonical semantics.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()

REQUIRED_FILES = [
    ".agent/endpoint-policy-contract.yml",
    "scripts/security/check_endpoint_policy_contract.py",
    ".github/workflows/endpoint-policy-contract.yml",
    "AGENTS.md",
]

REQUIRED_CONTRACT_STRINGS = [
    "endpoint-transport-policy",
    "diazMelgarejo/Perpetua-Tools",
    "diazMelgarejo/orama-system",
    "src/utils/endpoint_policy_core.py",
    "transport-identity",
    "preserve-scheme",
    "backend-port-isolation",
    "bin/orama-system/skills/oramasys-method/SKILL.md",
    "bin/orama-system/skills/oramasys-method/references/integrative-merge.md",
    "bin/orama-system/skills/git-history-surgery/SKILL.md",
]

REQUIRED_AGENTS_STRINGS = [
    "Endpoint transport policy",
    "diazMelgarejo/Perpetua-Tools",
    "src/utils/endpoint_policy_core.py",
    "bin/orama-system/skills/oramasys-method/SKILL.md",
    "docs/SECURITY-POLICY.md",
]

DOUBLE_SCHEME_MARKERS = ("http://" + "http", "https://" + "https")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def fail(message: str) -> None:
    raise SystemExit(f"endpoint policy contract failed: {message}")


def assert_required_files() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        fail(f"missing required files: {', '.join(missing)}")


def assert_contract() -> None:
    text = read(".agent/endpoint-policy-contract.yml")
    missing = [needle for needle in REQUIRED_CONTRACT_STRINGS if needle not in text]
    if missing:
        fail(f"contract missing required entries: {', '.join(missing)}")


def assert_agents_guidance() -> None:
    text = read("AGENTS.md")
    missing = [needle for needle in REQUIRED_AGENTS_STRINGS if needle not in text]
    if missing:
        fail(f"AGENTS.md missing endpoint guidance: {', '.join(missing)}")


def assert_workflow() -> None:
    text = read(".github/workflows/endpoint-policy-contract.yml")
    if "python scripts/security/check_endpoint_policy_contract.py" not in text:
        fail("endpoint-policy-contract workflow must run the contract checker")


def assert_no_double_scheme_literals() -> None:
    scan_roots = ["bin", "scripts"]
    for folder in scan_roots:
        root = ROOT / folder
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.resolve() == SELF:
                continue
            if path.is_file() and path.suffix in {".py", ".sh", ".md", ".yml", ".yaml", ".json"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
                if any(marker in text for marker in DOUBLE_SCHEME_MARKERS):
                    fail(f"double-scheme literal found in {path.relative_to(ROOT)}")


def main() -> None:
    assert_required_files()
    assert_contract()
    assert_agents_guidance()
    assert_workflow()
    assert_no_double_scheme_literals()
    print("endpoint policy peer contract passed")


if __name__ == "__main__":
    main()
