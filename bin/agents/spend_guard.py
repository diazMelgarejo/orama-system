"""Orama's adapter to the shared spend guard that lives in Perpetua-Tools.

Perpetua-Tools is the runtime and state authority (budget state, provider policies, attestations);
orama-system is stateless and consumes it. The adapter loads Perpetua-Tools'
`orchestrator/spend_gate.py` from PERPETUA_TOOLS_ROOT and forwards to its SpendGate: orama keeps no
ledger and no spend logic of its own, so the ceiling is the one shared, atomic budget Perpetua-Tools owns. It fails closed: with no checkout, no policy or no valid operator
attestation, a live request is refused. The estimate is not billing; the provider's Billing page is.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

DEFAULT_PROVIDER = "wandb-inference"
# One documented, git-ignored symlink to the Perpetua-Tools checkout that holds the shared guard.
# Resolution order: explicit argument, PERPETUA_TOOLS_ROOT, then this link. No global variable is
# needed, which matters: orama's own portal also reads PERPETUA_TOOLS_ROOT and a linked worktree
# there trips Perpetua-Tools' state-authority check.
LOCAL_LINK = Path(__file__).resolve().parents[2] / ".local" / "perpetua-tools"
# CI checkout of Perpetua-Tools (pinned by .github/pt-dispatch-test-ref).
CI_CHECKOUT = Path(__file__).resolve().parents[2] / ".ci" / "pt-dispatch"


class SpendGuardUnavailable(RuntimeError):
    """The shared guard cannot be loaded. A caller that asked for a budget must not proceed."""


def _has_guard(root: Path) -> bool:
    """True when ``root`` holds the shared spend gate (an older checkout without it is not a guard)."""
    return (root / "orchestrator" / "spend_gate.py").is_file()


def resolve_pt_root(explicit: str | Path | None = None) -> Path:
    """The Perpetua-Tools checkout holding the shared guard, or SpendGuardUnavailable.

    An explicit argument must be valid and is never second-guessed. Otherwise the first of
    PERPETUA_TOOLS_ROOT and the local symlink that actually contains the guard wins: the environment
    often names a checkout that predates the guard, and the symlink then supplies it.
    """
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not _has_guard(root):
            raise SpendGuardUnavailable(f"{root} does not contain the shared spend guard")
        return root
    tried: list[str] = []
    for label, raw in (
        ("PERPETUA_TOOLS_ROOT", os.environ.get("PERPETUA_TOOLS_ROOT")),
        ("local symlink", LOCAL_LINK if (LOCAL_LINK.exists() or LOCAL_LINK.is_symlink()) else None),
        ("CI checkout", CI_CHECKOUT if CI_CHECKOUT.exists() else None),
    ):
        if not raw:
            tried.append(f"{label}: not set")
            continue
        root = Path(raw).expanduser().resolve()
        if _has_guard(root):
            return root
        tried.append(f"{label}: no shared spend guard in {root.name}")
    raise SpendGuardUnavailable("no Perpetua-Tools checkout with the shared guard (" + "; ".join(tried) + ")")


def _load(root: Path, rel: str, name: str):
    """Import ``rel`` under ``root`` by file path as module ``name``; SpendGuardUnavailable if it cannot load."""
    path = root / rel
    if not path.is_file():
        raise SpendGuardUnavailable(f"{rel} not found under {root}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SpendGuardUnavailable(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class SpendGuard:
    """Preflight, settle and release one provider's spend by forwarding to Perpetua-Tools' SpendGate."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        pt_root: str | Path | None = None,
        state_dir: str | Path | None = None,
        now: Any = None,
    ) -> None:
        """Load the producer's gate. Any failure to obtain a valid policy or a safe store is a refusal."""
        root = resolve_pt_root(pt_root)
        module = _load(root, "orchestrator/spend_gate.py", "pt_spend_gate")
        try:
            self.gate = module.SpendGate(provider, state_dir=state_dir, now=now)
        except (module._pl.ProviderPolicyError, PermissionError) as exc:
            raise SpendGuardUnavailable(str(exc)) from exc
        self.provider = provider
        self.policy = self.gate.policy
        self.guard = self.gate.guard
        self.audit_path = self.gate.audit_path

    def preflight(self, prompt_chars: int, hold_seconds: float) -> dict:
        """Refuse (attestation, budget) or reserve the projected cost for ``hold_seconds``."""
        return self.gate.preflight(prompt_chars, hold_seconds)

    def settle(self, reservation: str, input_chars: int, output_chars: int, outcome: str, seat: str, mode: str) -> float:
        """Commit the estimated actual cost of an answered request. Returns the estimate."""
        return self.gate.settle(reservation, input_chars, output_chars, outcome, seat, mode)

    def settle_unknown(self, reservation: str, input_chars: int, outcome: str, seat: str, mode: str) -> float:
        """Commit the full reservation for a possibly sent request whose output is unavailable."""
        return self.gate.settle_unknown(reservation, input_chars, outcome, seat, mode)

    def release(self, reservation: str) -> None:
        """Release a reservation that was never sent. Idempotent."""
        self.gate.release(reservation)

    def classify(self, text: Any) -> str | None:
        """The shared policy's classification of a provider failure message, or None."""
        return self.gate.classify(text)

    def snapshot(self) -> dict:
        """The shared budget snapshot."""
        return self.gate.snapshot()
