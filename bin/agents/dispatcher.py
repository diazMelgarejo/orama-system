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

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


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

    # ── Direct binary subagent dispatch ────────────────────────────────────────

    async def dispatch_binary(
        self,
        *,
        binary: str,
        args: List[str],
        prompt: str,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[Path] = None,
        timeout_sec: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Dispatch a worker via a direct binary subagent (AntiGravity / Gemini).

        This bypasses PT's OrchestrationSupervisor and invokes the binary
        directly as a subprocess.  Use for verified subagent roles (e.g.
        antigravity-agent, gemini-agent) where direct binary execution is the
        proven working path.

        Environment variables EXA_API_KEY and FIRECRAWL_API_KEY are passed
        through from the caller's env so Exa and Firecrawl MCP servers can be
        resolved by the binary (per PT .agent memory: Exa uses
        orama-system/scripts/exa/exa-mcp-wrapper.sh as stdio MCP; Firecrawl
        uses npm install -g firecrawl-mcp + remote HTTP at
        https://mcp.firecrawl.dev/v2/mcp).

        Args:
            binary: Path to the binary executable (e.g. ANTIGRAVITY_BIN).
            args: CLI args for the binary.
            prompt: The prompt to pass to the subagent.
            env: Extra environment variables (merged with os.environ).
            cwd: Working directory for the subprocess.
            timeout_sec: Optional timeout in seconds.

        Returns:
            Parsed result dict from the binary's stdout (JSON expected).

        Raises:
            RuntimeError: if the binary exits non-zero or returns invalid JSON.
            asyncio.TimeoutError: if timeout_sec is exceeded.
        """
        full_env = dict(os.environ)
        if env:
            full_env.update(env)

        # Ensure EXA/FireCrawl API keys are available for MCP resolution
        for key in ("EXA_API_KEY", "FIRECRAWL_API_KEY"):
            if key not in full_env:
                full_env.pop(key, None)  # don't leak if absent

        proc = await asyncio.create_subprocess_exec(
            binary,
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env,
            cwd=str(cwd) if cwd else None,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=prompt.encode("utf-8")),
                timeout=timeout_sec,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise

        if proc.returncode != 0:
            err_text = stderr.decode("utf-8", errors="replace") if stderr else ""
            raise RuntimeError(
                f"Binary {binary} exited {proc.returncode}: {err_text}"
            )

        out_text = stdout.decode("utf-8", errors="replace")
        try:
            return json.loads(out_text)
        except json.JSONDecodeError:
            # Return raw text wrapped in a dict if not JSON
            return {"raw": out_text}

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
        direct_binary: bool = False,
        binary_path: Optional[str] = None,
        binary_args: Optional[List[str]] = None,
        binary_timeout_sec: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Dispatch one worker and return its result dict.

        PT is the default runtime authority; orama just builds the spec.
        This does NOT store state — orama is stateless.

        When direct_binary=True, bypasses PT's OrchestrationSupervisor and
        invokes the binary directly via dispatch_binary().  This is the
        AntiGravity/Gemini direct subagent path — use for verified roles where
        direct binary execution is the proven working path.

        Args:
            direct_binary: If True, use direct binary dispatch instead of PT.
            binary_path: Path to the binary (defaults to ANTIGRAVITY_BIN or
                GEMINI_BIN env var based on role).
            binary_args: CLI args for the binary.
            binary_timeout_sec: Optional timeout for binary execution.
        """
        if direct_binary:
            binary = binary_path or os.getenv(
                "ANTIGRAVITY_BIN" if "antigravity" in role.lower() else "GEMINI_BIN",
                "",
            )
            if not binary:
                raise RuntimeError(
                    f"direct_binary=True but no binary path for role={role!r}. "
                    "Set binary_path or ANTIGRAVITY_BIN/GEMINI_BIN env var."
                )
            return await self.dispatch_binary(
                binary=binary,
                args=binary_args or [],
                prompt=prompt,
                timeout_sec=binary_timeout_sec,
            )

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
