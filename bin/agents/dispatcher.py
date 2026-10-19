"""bin/agents/dispatcher.py — OramaToPTBridge: orama → PT dispatch layer.

orama is stateless; it plans, builds prompts, and returns results.
All durable dispatch — job queue, hardware affinity, GPU lock, LAN routing —
is owned by Perpetua-Tools (PT).  This module is orama's typed interface to PT.

Key invariants enforced here (per unified-absorption-plan.md § 5.5):
  - Crystallization NEVER fires without an approved VerificationResult.
    dispatch_crystallization() raises PermissionError if verdict != "approved".
  - Parallel fan-out is allowed for independent worker roles; results are
    collected and returned as a list — orama does not store them.
  - orama never imports from PT at module load time; imports are deferred
    inside methods so orama can be imported even without PERPETUATOOLSROOT.

Architecture (§ 5 contract):
    orama stage planner
        │
        ▼
    OramaToPTBridge.dispatch_*()   ← this file
        │  typed PT contracts
        ▼
    PT OrchestrationSupervisor (via HTTP or direct import)
        │  hardware affinity + job queue
        ▼
    Worker (Ollama / LM Studio Win / Codex / Gemini)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional


# ── PT path bootstrap ─────────────────────────────────────────────────────────
def _bootstrap_pt_path() -> Optional[Path]:
    """Add PT root to sys.path if PERPETUATOOLSROOT is set.  Silent on miss."""
    raw = os.getenv("PERPETUATOOLSROOT", "").strip()
    if not raw:
        return None
    pt = Path(raw).resolve()
    if pt.is_dir() and str(pt) not in sys.path:
        sys.path.insert(0, str(pt))
    return pt if pt.is_dir() else None


_PT_ROOT: Optional[Path] = _bootstrap_pt_path()


@dataclass(frozen=True)
class BinaryRegistration:
    """Discovery configuration; invocation and output contracts belong to PT."""

    env_var: str
    command: str


BINARY_REGISTRY: Mapping[str, BinaryRegistration] = MappingProxyType({
    "antigravity": BinaryRegistration("ANTIGRAVITY_BIN", "agy"),
    "gemini": BinaryRegistration("GEMINI_BIN", "gemini"),
    "codex": BinaryRegistration("CODEX_BIN", "codex"),
    "cursor": BinaryRegistration("CURSOR_BIN", "cursor-agent"),
    "claude": BinaryRegistration("CLAUDE_BIN", "claude"),
    "ollama": BinaryRegistration("OLLAMA_BIN", "ollama"),
    "windsurf": BinaryRegistration("WINDSURF_BIN", "windsurf"),
    "cline": BinaryRegistration("CLINE_BIN", "cline"),
    "kimi": BinaryRegistration("KIMI_BIN", "kimi"),
})


def _is_bare_command(candidate: str) -> bool:
    """True when ``candidate`` names a command to look up, not a pathname."""
    if "/" in candidate or "\\" in candidate:
        return False
    return not (sys.platform == "win32" and len(candidate) >= 2 and candidate[1] == ":")


def _search_path() -> str:
    """The ``PATH`` string used for lookup, with any quotes around entries removed.

    Windows ``PATH`` entries are often quoted, which ``shutil.which`` does not
    expect. An unset ``PATH`` falls back to ``os.defpath``.
    """
    raw = os.environ.get("PATH", os.defpath)
    return os.pathsep.join(entry.strip().strip('"') for entry in raw.split(os.pathsep))


def _search_path_entries() -> tuple[str, ...]:
    """Return trusted PATH directories, excluding empty current-directory entries."""
    return tuple(entry for entry in _search_path().split(os.pathsep) if entry)


def _windows_pathext() -> tuple[str, ...]:
    """Return the PATHEXT suffixes exactly as configured, in order, without empty entries."""
    return tuple(
        extension.strip()
        for extension in os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";")
        if extension.strip()
    )


def _windows_executable_extensions() -> tuple[str, ...]:
    """Return normalized executable suffixes used to compare, never to build, file names."""
    return tuple(extension.casefold() for extension in _windows_pathext())


def _find_bare_command(command: str) -> Optional[str]:
    """Find ``command`` only through explicit non-empty PATH directories.

    ``shutil.which`` can consult the working directory on Windows before a
    supplied PATH. Joining each approved directory ourselves keeps a planted
    local command from shadowing a later, configured installation.
    """
    for directory in _search_path_entries():
        base = Path(directory) / command
        candidates = (base,)
        if sys.platform == "win32":
            # File names use the PATHEXT casing as configured, so a case-sensitive
            # filesystem finds the same file Windows would; comparison is case-insensitive.
            candidates = (base, *(
                base.with_name(f"{base.name}{extension}") for extension in _windows_pathext()
            ))
            if base.suffix.casefold() not in _windows_executable_extensions():
                candidates = (*candidates[1:], base)
        for candidate in candidates:
            if candidate.is_file() and (sys.platform == "win32" or os.access(candidate, os.X_OK)):
                return str(candidate)
    return None


def resolve_binary_path(binary_name: str, explicit_path: Optional[str] = None) -> str:
    """Resolve an executable by explicit override, registered environment, then PATH.

    ``~`` is expanded. A candidate containing a path separator is a pathname,
    resolved as given (relative ones against the current directory); a bare
    name is looked up on ``PATH`` only. A configured but invalid override fails
    without falling back. Resolution is
    an availability check, not identity verification or permission to execute.
    No subprocess, shell interpolation, installation, or service start occurs.
    """
    entry = BINARY_REGISTRY.get(binary_name.lower())
    if entry is None:
        raise ValueError(f"Unknown binary {binary_name!r}; choose a registered agent")
    candidate = (
        explicit_path if explicit_path is not None
        else os.environ.get(entry.env_var, entry.command)
    )
    repair = (
        f"Set {entry.env_var} or --binary-path to an executable file, "
        f"or install {entry.command} on PATH"
    )
    if not candidate.strip() or "\x00" in candidate:
        raise ValueError(f"Invalid executable configuration. {repair}")
    candidate = os.path.expanduser(candidate)
    found = _find_bare_command(candidate) if _is_bare_command(candidate) else shutil.which(candidate)
    if found is None or not Path(found).is_file():
        raise ValueError(f"Agent executable is unavailable or not executable. {repair}")
    if sys.platform == "win32":
        # Python 3.10/3.11 which() can accept any directly named regular file.
        extensions = set(_windows_executable_extensions())
        if Path(found).suffix.casefold() not in extensions:
            raise ValueError(f"Agent executable has no permitted Windows extension. {repair}")
    return os.path.abspath(found)


def main(argv: Optional[List[str]] = None) -> int:
    """Print JSON executable preflight evidence without dispatching an agent."""
    parser = argparse.ArgumentParser(description="Check agent executable availability without execution")
    parser.add_argument("--check-binary", required=True, choices=sorted(BINARY_REGISTRY))
    parser.add_argument("--binary-path", help="Explicit executable override")
    args = parser.parse_args(argv)
    try:
        path = resolve_binary_path(args.check_binary, args.binary_path)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps({"binary": args.check_binary, "path": path}))
    return 0


# ── OramaToPTBridge ───────────────────────────────────────────────────────────

class OramaToPTBridge:
    """Typed dispatch bridge from orama stage planner to PT workers.

    All methods are async.  orama creates one bridge instance per orchestration
    session and calls dispatch_*() for each stage.

    Verifier gate (CLAUDE.md § 0 — absolute contract):
      dispatch_crystallization() raises PermissionError unless the provided
      VerificationResult has verdict == "approved".  This is enforced in code,
      not convention.
    """

    def __init__(
        self,
        *,
        session_id: str,
        parent_orchestrator_id: str,
        pt_root: Optional[Path] = None,
    ) -> None:
        self.session_id = session_id
        self.parent_orchestrator_id = parent_orchestrator_id
        self._pt_root = pt_root or _PT_ROOT

    # ── Single worker dispatch ─────────────────────────────────────────────────

    async def dispatch_worker(
        self,
        *,
        role: str,
        intent: str,
        prompt: str,
        specialization: Optional[str] = None,
        backend_hint: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        constraints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Dispatch one worker through PT and return its result dict.

        PT is the runtime authority; orama just builds the spec.
        This does NOT store state — orama is stateless.
        """
        spec = self._build_spec(
            role=role,
            intent=intent,
            prompt=prompt,
            specialization=specialization,
            backend_hint=backend_hint,
            metadata=metadata or {},
            constraints=constraints or [],
        )
        return await self._run_via_pt(spec)

    # ── Parallel fan-out ───────────────────────────────────────────────────────

    async def dispatch_parallel(
        self,
        workers: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Dispatch multiple independent workers concurrently.

        Each element of ``workers`` must have at least ``role``, ``intent``,
        and ``prompt`` keys.  Additional keys map to dispatch_worker() kwargs.

        Results are returned in the same order as ``workers``.
        """
        tasks = [
            asyncio.create_task(
                self.dispatch_worker(
                    role=w["role"],
                    intent=w["intent"],
                    prompt=w["prompt"],
                    specialization=w.get("specialization"),
                    backend_hint=w.get("backend_hint"),
                    metadata=w.get("metadata", {}),
                    constraints=w.get("constraints", []),
                )
            )
            for w in workers
        ]
        return list(await asyncio.gather(*tasks))

    # ── Verifier gate (hard-enforced) ─────────────────────────────────────────

    async def dispatch_crystallization(
        self,
        *,
        prompt: str,
        verification_result: Any,  # orchestrator.contracts.VerificationResult
        metadata: Optional[Dict[str, Any]] = None,
        constraints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Dispatch the crystallizer worker — ONLY if verification passed.

        Raises:
            PermissionError: if verification_result.verdict != "approved".
                This is the verifier gate (CLAUDE.md § 0 absolute contract).
                Callers must not catch this to bypass; fix the work instead.
        """
        verdict = getattr(verification_result, "verdict", None)
        if verdict != "approved":
            raise PermissionError(
                f"Crystallization blocked: VerificationResult.verdict == {verdict!r}. "
                "Verdict must be 'approved' before crystallization can proceed. "
                "Fix the work and re-verify."
            )
        return await self.dispatch_worker(
            role="crystallizer-agent",
            intent="crystallize",
            prompt=prompt,
            metadata=metadata or {},
            constraints=constraints or [],
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _build_spec(
        self,
        *,
        role: str,
        intent: str,
        prompt: str,
        specialization: Optional[str],
        backend_hint: Optional[str],
        metadata: Dict[str, Any],
        constraints: List[str],
    ) -> Any:
        """Build a PT JobSpec.  Imports PT at call time to avoid boot-time deps."""
        try:
            from orchestrator.supervisor import JobSpec  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "Cannot import PT's JobSpec. "
                "Set PERPETUATOOLSROOT to the Perpetua-Tools root directory."
            ) from exc

        return JobSpec(
            intent=intent,
            prompt=prompt,
            role=role,
            specialization=specialization,
            backend_hint=backend_hint,
            metadata={**metadata, "session_id": self.session_id},
            constraints=constraints,
            session_id=self.session_id,
            parent_orchestrator_id=self.parent_orchestrator_id,
        )

    async def _run_via_pt(self, spec: Any) -> Dict[str, Any]:
        """Submit spec to PT's OrchestrationSupervisor and await result.

        In V1 we import PT directly (same process, sibling repo).
        V2 upgrade path: replace with an HTTP call to PT's FastAPI surface.
        """
        try:
            from orchestrator.supervisor import OrchestrationSupervisor  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "Cannot import PT's OrchestrationSupervisor. "
                "Set PERPETUATOOLSROOT to the Perpetua-Tools root directory."
            ) from exc

        sup = OrchestrationSupervisor()
        job_id = await sup.submit_job(spec)

        # Poll until the job reaches a terminal state
        while True:
            status = await sup.get_status(job_id)
            if status is None:
                await asyncio.sleep(0.05)
                continue
            state = status.get("status", "")
            if state in {"succeeded", "failed", "cancelled"}:
                break
            await asyncio.sleep(0.1)

        result = status.get("result") or {}
        if status.get("status") != "succeeded":
            error = status.get("error", "unknown error")
            raise RuntimeError(f"PT worker failed (job={job_id}): {error}")
        return result


if __name__ == "__main__":
    raise SystemExit(main())
