from __future__ import annotations

import pytest

from orama_system import swarm_approval

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _isolated_swarm_approval_state(monkeypatch: pytest.MonkeyPatch):
    swarm_approval._cache.clear()
    for key in (
        "ORAMA_SWARM_APPROVAL_SECRET",
        "ORAMA_SWARM_STRICT",
        "ORAMA_SWARM_LEGACY_APPROVE",
        "ORAMA_CONTROL_PLANE_TOKEN",
        "GOSSIP_SHARED_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)
    yield
    swarm_approval._cache.clear()


def test_issue_approval_fails_closed_without_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    preview = {"objective": "x", "assignments": [], "task_type": "implementation"}
    with pytest.raises(ValueError, match="secret"):
        swarm_approval.issue_approval(preview)
    with pytest.raises(ValueError, match="preview_id"):
        swarm_approval.verify_launch(approved=True, preview_id=None, approval_token=None, preview=preview)


def test_legacy_approve_defaults_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ORAMA_SWARM_STRICT", raising=False)
    monkeypatch.delenv("ORAMA_SWARM_LEGACY_APPROVE", raising=False)
    preview = {"objective": "x", "assignments": [], "task_type": "implementation"}
    with pytest.raises(ValueError, match="preview_id"):
        swarm_approval.verify_launch(approved=True, preview_id=None, approval_token=None, preview=preview)


def test_grandfather_legacy_approve(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ORAMA_SWARM_STRICT", raising=False)
    monkeypatch.setenv("ORAMA_SWARM_LEGACY_APPROVE", "1")
    preview = {"objective": "x", "assignments": [], "task_type": "implementation"}
    swarm_approval.verify_launch(approved=True, preview_id=None, approval_token=None, preview=preview)


def test_legacy_empty_env_does_not_grandfather(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ORAMA_SWARM_STRICT", raising=False)
    monkeypatch.setenv("ORAMA_SWARM_LEGACY_APPROVE", "")
    assert swarm_approval.grandfather_legacy() is False
    preview = {"objective": "x", "assignments": [], "task_type": "implementation"}
    with pytest.raises(ValueError, match="preview_id"):
        swarm_approval.verify_launch(approved=True, preview_id=None, approval_token=None, preview=preview)


def test_legacy_rejects_blank_preview_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ORAMA_SWARM_STRICT", raising=False)
    monkeypatch.setenv("ORAMA_SWARM_LEGACY_APPROVE", "1")
    preview = {"objective": "x", "assignments": [], "task_type": "implementation"}
    with pytest.raises(ValueError, match="preview_id"):
        swarm_approval.verify_launch(approved=True, preview_id="", approval_token="", preview=preview)


def test_strict_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORAMA_SWARM_STRICT", "1")
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    preview = {"objective": "x", "assignments": [], "task_type": "implementation"}
    with pytest.raises(ValueError, match="preview_id"):
        swarm_approval.verify_launch(approved=False, preview_id=None, approval_token=None, preview=preview)


def test_issue_and_verify_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORAMA_SWARM_STRICT", "1")
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    preview = {"objective": "ship", "assignments": [{"role": "a"}], "task_type": "implementation"}
    issued = swarm_approval.issue_approval(preview)

    tampered_preview = {**preview, "objective": "tampered"}
    with pytest.raises(ValueError, match="preview drift"):
        swarm_approval.verify_launch(
            approved=True,
            preview_id=issued["preview_id"],
            approval_token=issued["approval_token"],
            preview=tampered_preview,
        )

    swarm_approval.verify_launch(
        approved=True,
        preview_id=issued["preview_id"],
        approval_token=issued["approval_token"],
        preview=preview,
    )

    issued2 = swarm_approval.issue_approval(preview)
    with pytest.raises(ValueError, match="invalid approval_token"):
        swarm_approval.verify_launch(
            approved=True,
            preview_id=issued2["preview_id"],
            approval_token="deadbeef" * 8,
            preview=preview,
        )

    issued3 = swarm_approval.issue_approval(preview)
    with pytest.raises(ValueError, match="invalid approval_token"):
        swarm_approval.verify_launch(
            approved=True,
            preview_id=issued3["preview_id"],
            approval_token="short",
            preview=preview,
        )


def test_cached_preview_is_isolated_from_caller_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    preview = {
        "objective": "ship",
        "assignments": [{"role": "context-agent"}],
        "task_type": "implementation",
        "optimize_for": "reliability",
        "preferred_device": "auto",
    }
    issued = swarm_approval.issue_approval(preview)
    preview["assignments"][0]["role"] = "tampered"
    preview.update(issued)

    first = swarm_approval.cached_preview(issued["preview_id"])
    assert first is not None
    assert first["assignments"][0]["role"] == "context-agent"
    assert "approval_token" not in first
    assert "preview_id" not in first

    first["objective"] = "mutated returned copy"
    second = swarm_approval.cached_preview(issued["preview_id"])
    assert second is not None
    assert second["objective"] == "ship"


def test_cached_preview_evicts_expired_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    preview = {"objective": "x", "assignments": [], "task_type": "implementation"}
    issued = swarm_approval.issue_approval(preview)
    preview_id = issued["preview_id"]
    _, issued_at, _ = swarm_approval._cache[preview_id]
    monkeypatch.setattr(
        swarm_approval.time,
        "time",
        lambda: issued_at + swarm_approval._PREVIEW_TTL_SEC + 1,
    )

    assert swarm_approval.cached_preview(preview_id) is None
    assert preview_id not in swarm_approval._cache


def test_cache_never_exceeds_max_size(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    preview = {"objective": "x", "assignments": [], "task_type": "implementation"}

    for _ in range(swarm_approval._MAX_CACHE_SIZE + 5):
        swarm_approval.issue_approval(preview)

    assert len(swarm_approval._cache) == swarm_approval._MAX_CACHE_SIZE


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("optimize_for", "speed"),
        ("preferred_device", "windows"),
    ],
)
def test_fingerprint_covers_all_dispatched_options(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    changed: str,
) -> None:
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    preview = {
        "objective": "ship",
        "assignments": [],
        "task_type": "implementation",
        "optimize_for": "reliability",
        "preferred_device": "auto",
    }
    issued = swarm_approval.issue_approval(preview)

    with pytest.raises(ValueError, match="preview drift"):
        swarm_approval.check_launch(
            approved=True,
            preview_id=issued["preview_id"],
            approval_token=issued["approval_token"],
            preview={**preview, field: changed},
        )


def test_claim_launch_is_exclusive(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only one ``claim_launch_for_dispatch`` succeeds per preview_id at a time."""
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    preview = {"objective": "ship", "assignments": [], "task_type": "implementation"}
    issued = swarm_approval.issue_approval(preview)
    launch_preview = {**preview, "objective": "ship"}

    stored, attempt = swarm_approval.claim_launch_for_dispatch(
        approved=True,
        preview_id=issued["preview_id"],
        approval_token=issued["approval_token"],
        preview=launch_preview,
    )
    assert stored["objective"] == "ship"
    with pytest.raises(ValueError, match="expired or unknown"):
        swarm_approval.claim_launch_for_dispatch(
            approved=True,
            preview_id=issued["preview_id"],
            approval_token=issued["approval_token"],
            preview=launch_preview,
        )
    swarm_approval.finalize_launch_claim(issued["preview_id"], attempt)


def test_check_launch_does_not_consume_but_consume_is_single_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    preview = {"objective": "ship", "assignments": [], "task_type": "implementation"}
    issued = swarm_approval.issue_approval(preview)

    for _ in range(2):
        swarm_approval.check_launch(
            approved=True,
            preview_id=issued["preview_id"],
            approval_token=issued["approval_token"],
            preview=preview,
        )

    swarm_approval.consume_launch(issued["preview_id"])
    with pytest.raises(ValueError, match="expired or unknown"):
        swarm_approval.consume_launch(issued["preview_id"])


def test_token_without_explicit_approval_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORAMA_SWARM_STRICT", "1")
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    preview = {"objective": "ship", "assignments": [], "task_type": "implementation"}
    issued = swarm_approval.issue_approval(preview)
    with pytest.raises(ValueError, match="explicit approval"):
        swarm_approval.verify_launch(
            approved=False,
            preview_id=issued["preview_id"],
            approval_token=issued["approval_token"],
            preview=preview,
        )


def test_approval_is_single_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORAMA_SWARM_STRICT", "1")
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    preview = {"objective": "once", "assignments": [], "task_type": "implementation"}
    issued = swarm_approval.issue_approval(preview)
    swarm_approval.verify_launch(
        approved=True,
        preview_id=issued["preview_id"],
        approval_token=issued["approval_token"],
        preview=preview,
    )
    with pytest.raises(ValueError, match="expired or unknown"):
        swarm_approval.verify_launch(
            approved=True,
            preview_id=issued["preview_id"],
            approval_token=issued["approval_token"],
            preview=preview,
        )
