"""Compatibility controller for Orama lesson capture backends.

V1 delegates development lessons to the PT Agentic-Stack portable brain.
The runtime Anamnesis backend is deliberately unavailable until its repository
and provisioning contract exist; fail closed instead of silently creating a
second untracked memory system.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Protocol


class LessonBackendUnavailable(RuntimeError):
    """A requested backend cannot be used in the current installation."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class LessonPayload:
    pattern: str
    what_went_wrong: str
    root_cause: str
    prevention_rule: str
    verification_trigger: str
    applied_to: str
    good_example: str
    bad_example: str

    def claim(self) -> str:
        return f"{self.pattern}: {self.prevention_rule}"

    def rationale(self) -> str:
        return "\n".join(
            (
                f"What went wrong: {self.what_went_wrong}",
                f"Root cause: {self.root_cause}",
                f"Verification trigger: {self.verification_trigger}",
                f"Applied to: {self.applied_to}",
                f"Good example: {self.good_example}",
                f"Bad example: {self.bad_example}",
            )
        )

    def markdown(self) -> str:
        date = datetime.now().strftime("%Y-%m-%d")
        return f"""
## {date} — {self.pattern}

### What Went Wrong
{self.what_went_wrong}

### Root Cause
{self.root_cause}

### Prevention Rule
{self.prevention_rule}

### Verification Trigger
{self.verification_trigger}

### Applied To
{self.applied_to}

### Examples
✅ **Good**: {self.good_example}
❌ **Bad**: {self.bad_example}

---
"""


class LessonBackend(Protocol):
    def capture(self, payload: LessonPayload) -> None: ...


class PTAgentBackend:
    """Adapter to PT's existing tracked Agentic-Stack lesson pipeline."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.learn = root / ".agent" / "tools" / "learn.py"
        if not self.learn.is_file():
            raise LessonBackendUnavailable(
                "ORAMASYS_LESSON_E_PT_AGENT_UNAVAILABLE",
                f"PT Agentic-Stack learn.py not found at configured root: {root}",
            )

    def capture(self, payload: LessonPayload) -> None:
        result = subprocess.run(
            [sys.executable, str(self.learn), payload.claim(), "--rationale", payload.rationale()],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
            raise LessonBackendUnavailable(
                "ORAMASYS_LESSON_E_PT_AGENT_CAPTURE",
                f"PT Agentic-Stack lesson capture failed: {detail}",
            )


class LegacyMarkdownBackend:
    """Read and update an already-initialized standalone legacy log only."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def capture(self, payload: LessonPayload) -> None:
        if not self.path.is_file():
            raise LessonBackendUnavailable(
                "ORAMASYS_LESSON_E_LEGACY_UNINITIALIZED",
                "Legacy lesson capture is available only for an existing compatibility "
                f"log; no new v1 user-level log will be created at {self.path}.",
            )
        existing = self.path.read_text(encoding="utf-8")
        # Write the complete replacement and atomically swap it into place so a
        # killed capture process cannot leave an incomplete lesson log behind.
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(existing)
            stream.write(payload.markdown())
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self.path)


class DeferredAnamnesisBackend:
    """Explicit v2 boundary: no runtime store exists until provisioned."""

    @staticmethod
    def unavailable() -> LessonBackendUnavailable:
        return LessonBackendUnavailable(
            "ORAMASYS_LESSON_E_ANAMNESIS_UNAVAILABLE",
            "Runtime lesson storage requires provisioned oramasys/anamnesis; "
            "configure it during v2 provisioning before capture.",
        )

    def capture(self, _payload: LessonPayload) -> None:
        raise self.unavailable()


def resolve_backend(
    *,
    mode: str,
    backend_name: str,
    pt_root: Path | None,
    legacy_path: Path | None = None,
) -> LessonBackend:
    """Resolve the lowest-fragmentation backend for the selected context."""
    if backend_name == "auto":
        backend_name = "anamnesis" if mode == "runtime" else "pt-agent"
    if backend_name == "anamnesis":
        return DeferredAnamnesisBackend()
    if backend_name == "pt-agent":
        if pt_root is None:
            raise LessonBackendUnavailable(
                "ORAMASYS_LESSON_E_PT_AGENT_UNAVAILABLE",
                "Development lesson capture requires PERPETUA_TOOLS_ROOT; "
                "use --backend legacy only for an intentional standalone compatibility path.",
            )
        return PTAgentBackend(pt_root)
    if backend_name == "legacy":
        return LegacyMarkdownBackend(legacy_path or Path.home() / "tasks" / "lessons.md")
    raise LessonBackendUnavailable(
        "ORAMASYS_LESSON_E_BACKEND_INVALID", f"Unknown lesson backend: {backend_name}"
    )
