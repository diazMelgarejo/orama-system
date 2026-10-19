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


# ── Binary registry ──────────────────────────────────────────────────────────
#
# Each entry describes how to locate and invoke a supported subagent binary.
#   env_var         — environment variable holding the binary path
#   default_args    — CLI args prepended to every invocation
#   variable_syntax — how variables/prompt are passed:
#       "env"     → prompt + variables via environment variables
#       "flag"    → prompt + variables via CLI flags
#       "stdin"   → prompt via stdin, variables via environment
#   output_format   — "json" or "raw"
#

BINARY_REGISTRY: Dict[str, Dict[str, Any]] = {
    "antigravity": {
        "env_var": "ANTIGRAVITY_BIN",
        "default_args": [],
        "variable_syntax": "stdin",
        "output_format": "json",
    },
    "gemini": {
        "env_var": "GEMINI_BIN",
        "default_args": [],
        "variable_syntax": "stdin",
        "output_format": "json",
    },
    "codex": {
        "env_var": "CODEX_BIN",
        "default_args": [],
        "variable_syntax": "stdin",
        "output_format": "json",
    },
    "cursor": {
        "env_var": "CURSOR_BIN",
        "default_args": [],
        "variable_syntax": "stdin",
        "output_format": "json",
    },
    "claude": {
        "env_var": "CLAUDE_BIN",
        "default_args": [],
        "variable_syntax": "stdin",
        "output_format": "json",
    },
    "ollama": {
        "env_var": "OLLAMA_BIN",
        "default_args": ["serve"],
        "variable_syntax": "flag",
        "output_format": "raw",
    },
    "windsurf": {
        "env_var": "WINDSURF_BIN",
        "default_args": [],
        "variable_syntax": "stdin",
        "output_format": "json",
    },
}


def resolve_binary_path(
    binary_name: str, explicit_path: Optional[str] = None
) -> str:
    """Resolve a binary path from the registry or an explicit path.

    Priority:
      1. explicit_path argument
      2. The binary's registered env var
    """
    if explicit_path:
        return explicit_path

    entry = BINARY_REGISTRY.get(binary_name.lower())
    if entry:
        env_path = os.getenv(entry["env_var"], "")
        if env_path:
            return env_path

    raise RuntimeError(
        f"Cannot resolve binary '{binary_name}': no explicit path given and "
        f"environment variable not set. Register in BINARY_REGISTRY or set "
        f"the corresponding env var."
    )


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

    # ── Single worker dispatch (PT path) ─────────────────────────────────────

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
        binary_name: Optional[str] = None,
        binary_path: Optional[str] = None,
        binary_args: Optional[List[str]] = None,
        binary_timeout_sec: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Dispatch one worker and return its result dict.

        PT is the default runtime authority; orama just builds the spec.
        This does NOT store state — orama is stateless.

        When direct_binary=True, bypasses PT's OrchestrationSupervisor and
        invokes the binary directly via dispatch_binary().  Supported binaries
        are listed in BINARY_REGISTRY.
        """
        if direct_binary:
            if binary_path:
                binary = binary_path
            elif binary_name:
                entry = BINARY_REGISTRY.get(binary_name.lower())
                if not entry:
                    raise RuntimeError(
                        f"Unknown binary_name={binary_name!r}. "
                        f"Registered: {list(BINARY_REGISTRY)}"
                    )
                binary = os.getenv(entry["env_var"], "")
                if not binary:
                    raise RuntimeError(
                        f"Env var {entry['env_var']!r} not set for "
                        f"binary_name={binary_name!r}"
                    )
            else:
                raise RuntimeError(
                    "direct_binary=True requires binary_path or binary_name"
                )

            entry = BINARY_REGISTRY.get(binary_name.lower() if binary_name else {})
            args = (entry.get("default_args", []) if entry else []) + (
                binary_args or []
            )
            return await self.dispatch_binary(
                binary=binary,
                args=args,
                prompt=prompt,
                variable_syntax=(
                    entry.get("variable_syntax", "stdin") if entry else "stdin"
                ),
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

    # ── Common debug wrapper for all binaries ─────────────────────────────────

    async def dispatch_debug(
        self,
        *,
        binary_name: str,
        prompt: str,
        variables: Optional[Dict[str, str]] = None,
        debug_wrapper: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        timeout_sec: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Debug a subagent binary using its registered variable syntax.

        This is a common wrapper that works with ALL registered binaries
        (antigravity, gemini, codex, cursor, claude, ollama, windsurf).
        It respects each binary's ``variable_syntax`` from BINARY_REGISTRY:

          * "env"     → variables set as env vars, prompt via stdin
          * "flag"    → variables as CLI flags (--key value), prompt via stdin
          * "stdin"   → prompt via stdin, variables via env vars

        An optional ``debug_wrapper`` (e.g. "strace", "lldb --batch") is
        prepended to the command so the binary can be inspected under a
        debugger.

        Args:
            binary_name: Registered binary name from BINARY_REGISTRY.
            prompt: The prompt to pass to the binary.
            variables: Key-value pairs passed per the binary's variable_syntax.
            debug_wrapper: Optional wrapper command (e.g. "strace -f").
            extra_args: Additional CLI args appended after default_args.
            timeout_sec: Optional timeout in seconds.

        Returns:
            Parsed result dict from the binary's stdout.

        Raises:
            RuntimeError: if binary cannot be resolved or exits non-zero.
        """
        entry = BINARY_REGISTRY.get(binary_name.lower())
        if not entry:
            raise RuntimeError(
                f"Unknown binary_name={binary_name!r}. "
                f"Registered: {list(BINARY_REGISTRY)}"
            )

        binary = os.getenv(entry["env_var"], "")
        if not binary:
            raise RuntimeError(
                f"Env var {entry['env_var']!r} not set for "
                f"binary_name={binary_name!r}"
            )

        variable_syntax = entry.get("variable_syntax", "stdin")
        default_args = entry.get("default_args", [])

        # Build the command: [debug_wrapper, binary, *default_args, *extra_args]
        cmd: List[str] = []
        if debug_wrapper:
            cmd.append(debug_wrapper)
        cmd.append(binary)
        cmd.extend(default_args)
        if extra_args:
            cmd.extend(extra_args)

        full_env = dict(os.environ)

        if variable_syntax == "flag":
            # Variables passed as CLI flags: --key value
            if variables:
                for key, val in variables.items():
                    cmd.extend([f"--{key}", str(val)])
        elif variable_syntax in ("env", "stdin"):
            # Variables passed via environment
            if variables:
                for key, val in variables.items():
                    full_env[key] = str(val)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env,
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
                f"Binary {binary} (debug) exited {proc.returncode}: {err_text}"
            )

        out_text = stdout.decode("utf-8", errors="replace")
        try:
            return json.loads(out_text)
        except json.JSONDecodeError:
            return {"raw": out_text, "binary": binary_name, "command": cmd}

        return await self._run_via_pt(spec)
