"""Orama's adapter to the shared spend guard that lives in Perpetua-Tools.

Perpetua-Tools is the runtime and state authority (budget state, provider policies, attestations);
orama-system is stateless and consumes it. The adapter loads Perpetua-Tools'
`orchestrator/provider_limits.py` and `orchestrator/cost_guard.py` from PERPETUA_TOOLS_ROOT and adds
no spend logic of its own. It fails closed: with no checkout, no policy or no valid operator
attestation, a live request is refused. The estimate is not billing; the provider's Billing page is.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from datetime import datetime, timezone
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
    return (root / "orchestrator" / "provider_limits.py").is_file() and (root / "orchestrator" / "cost_guard.py").is_file()


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
    """Preflight, settle and release one provider's spend through Perpetua-Tools' CostGuard."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        pt_root: str | Path | None = None,
        state_dir: str | Path | None = None,
        now: Any = None,
    ) -> None:
        root = resolve_pt_root(pt_root)
        self.pl = _load(root, "orchestrator/provider_limits.py", "pt_provider_limits")
        self.cg = _load(root, "orchestrator/cost_guard.py", "pt_cost_guard")
        try:
            self.policy = self.pl.load_policy(provider)
        except self.pl.ProviderPolicyError as exc:
            raise SpendGuardUnavailable(str(exc)) from exc
        self.provider = provider
        self._now = now or (lambda: datetime.now(timezone.utc))
        spend = Path(state_dir) if state_dir else self.pl.spend_dir()
        self.guard = self.cg.CostGuard(
            state_dir=str(spend), budget_file=f"{provider}-budget.json", period=self.policy["budget"]["period"]
        )
        ceiling = float(self.policy["budget"]["operator_estimate_ceiling_usd"])
        if self.guard.snapshot()["daily_budget"] != ceiling:
            self.guard.set_budget(ceiling)  # the policy file is the source of truth for the ceiling
        self.audit_path = spend / f"{provider}-spend-audit.jsonl"

    def _attestation(self) -> Any:
        import json

        path = self.pl.attestation_path(self.provider)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            return {}

    def preflight(self, prompt_chars: int) -> dict:
        """Check the operator attestation, then reserve the projected cost against the budget."""
        status = self.pl.attestation_status(self.policy, self._attestation(), self._now())
        if not status["ok"]:
            return {"ok": False, "reason": "attestation-required", "stop": True, "reasons": status["reasons"]}
        projected = self.pl.projected_usd(self.policy, prompt_chars)
        try:
            reservation = asyncio.run(self.guard.reserve(projected))
        except self.cg.BudgetExceededError as exc:
            return {"ok": False, "reason": "budget-exhausted", "stop": True, "error": str(exc),
                    "projected_usd": projected}
        return {"ok": True, "reservation": reservation, "projected_usd": projected}

    def settle(self, reservation: str, input_chars: int, output_chars: int, outcome: str, seat: str, mode: str) -> float:
        """Commit the estimated actual cost and append a size-only audit row. Returns the estimate."""
        usd = self.pl.estimate_usd(self.policy, input_chars, output_chars)
        asyncio.run(self.guard.commit(reservation, usd))
        self.pl.append_audit(self.audit_path, {
            "ts": self._now().isoformat(), "seat": seat, "mode": mode, "input_chars": input_chars,
            "output_chars": output_chars, "estimated_usd": usd, "estimated": True, "outcome": outcome,
            "provider": self.provider, "policy_id": self.policy["policy_id"],
        })
        return usd

    def release(self, reservation: str) -> None:
        """Idempotent: a reservation that is already settled or released is not an error, so cleanup that
        follows a settle never masks the original failure."""
        try:
            asyncio.run(self.guard.rollback(reservation))
        except self.cg.UnknownReservationError:
            pass

    def classify(self, text: Any) -> str | None:
        return self.pl.classify_failure(self.policy, text)

    def snapshot(self) -> dict:
        return self.guard.snapshot()
