"""Tests for oramaclaw.merge — three-way SSA merge planner."""
from __future__ import annotations

from typing import Any

import pytest

from oramaclaw.merge import (
    FieldAction,
    MergePlan,
    extract_field,
    plan_resource,
    resource_key,
)
from oramaclaw.store import _fingerprint
from oramaclaw.types import MergePolicy, Resource, ResourceKind


# ── Fakes ─────────────────────────────────────────────────────────────────────

class FakeStore:
    """Minimal stand-in for ControlStore exposing only what plan_resource uses.

    ``fingerprints`` maps ``<resource_key><managed_path>`` → base fingerprint.
    ``overrides``    maps ``<resource_key><managed_path>`` → override dict
                     (keys: ``source_field_fingerprint``, ``observed_value``).
    """

    def __init__(
        self,
        fingerprints: dict[str, str] | None = None,
        overrides: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self._fingerprints = fingerprints or {}
        self._overrides = overrides or {}

    def field_fingerprint(self, resource_key: str, managed_path: str) -> str | None:
        return self._fingerprints.get(f"{resource_key}{managed_path}")

    def get_auto_weave_override(
        self, resource_key: str, managed_path: str
    ) -> dict[str, Any] | None:
        return self._overrides.get(f"{resource_key}{managed_path}")


# ── Builders ──────────────────────────────────────────────────────────────────

def _resource(
    *,
    kind: ResourceKind = ResourceKind.PROVIDER,
    identifier: str = "example-provider",
    policy: MergePolicy = MergePolicy.COOPERATIVE,
    path: str = "/effort",
    desired: Any = "high",
) -> Resource:
    return Resource(
        kind=kind,
        identifier=identifier,
        manager="oramaclaw",
        spec={"effort": desired} if path == "/effort" else _nested_spec(path, desired),
        managed_paths=(path,),
        policy=policy,
    )


def _nested_spec(json_pointer: str, value: Any) -> dict:
    root: dict = {}
    node = root
    tokens = json_pointer.strip("/").split("/")
    for tok in tokens[:-1]:
        node[tok] = {}
        node = node[tok]
    node[tokens[-1]] = value
    return root


def _key(resource: Resource, path: str) -> str:
    return f"{resource_key(resource)}{path}"


def _action(plan: MergePlan, path: str = "/effort") -> FieldAction:
    for act in plan.actions:
        if act.managed_path == path:
            return act
    raise AssertionError(f"no action for {path}")


# ── Resolution tests ──────────────────────────────────────────────────────────

def test_skip_when_already_correct():
    res = _resource(desired="high")
    live = {"effort": "high"}
    plan = plan_resource(res, live, FakeStore())
    assert _action(plan).kind == "skip"
    assert plan.conflicts == ()
    assert plan.auto_woven == ()


def test_apply_on_first_adoption():
    res = _resource(desired="high")
    live = {"effort": "low"}  # observed differs, base is None
    plan = plan_resource(res, live, FakeStore())
    act = _action(plan)
    assert act.kind == "apply"
    assert act.desired_value == "high"


def test_apply_when_base_equals_observed():
    res = _resource(desired="high")
    live = {"effort": "low"}
    # Manager last recorded "low"; observed is still "low" → clean ownership.
    store = FakeStore(fingerprints={_key(res, "/effort"): _fingerprint("low")})
    plan = plan_resource(res, live, store)
    act = _action(plan)
    assert act.kind == "apply"
    assert act.desired_value == "high"


def test_strict_policy_always_conflicts_on_drift():
    res = _resource(policy=MergePolicy.STRICT, desired="high")
    live = {"effort": "drifted"}
    # base != observed (base recorded as "low", observed "drifted").
    store = FakeStore(fingerprints={_key(res, "/effort"): _fingerprint("low")})
    plan = plan_resource(res, live, store)
    assert _action(plan).kind == "conflict"
    assert len(plan.conflicts) == 1
    assert plan.conflicts[0].security_topology is False


def test_security_topology_always_conflicts():
    res = _resource(
        kind=ResourceKind.DELEGATION,
        policy=MergePolicy.COOPERATIVE,
        desired="high",
    )
    live = {"effort": "drifted"}
    store = FakeStore(fingerprints={_key(res, "/effort"): _fingerprint("low")})
    plan = plan_resource(res, live, store)
    assert _action(plan).kind == "conflict"
    assert len(plan.conflicts) == 1
    assert plan.conflicts[0].security_topology is True
    assert plan.auto_woven == ()


def test_cooperative_drift_auto_woven():
    res = _resource(policy=MergePolicy.COOPERATIVE, desired="high")
    live = {"effort": "drifted"}
    store = FakeStore(fingerprints={_key(res, "/effort"): _fingerprint("low")})
    plan = plan_resource(res, live, store)
    act = _action(plan)
    assert act.kind == "auto_weave"
    assert "/effort" in plan.auto_woven
    assert plan.conflicts == ()


def test_cooperative_override_respected():
    res = _resource(policy=MergePolicy.COOPERATIVE, desired="high")
    live = {"effort": "drifted"}
    store = FakeStore(
        fingerprints={_key(res, "/effort"): _fingerprint("low")},
        overrides={
            _key(res, "/effort"): {
                "source_field_fingerprint": _fingerprint("high"),
                "observed_value": "drifted",
            }
        },
    )
    plan = plan_resource(res, live, store)
    assert _action(plan).kind == "skip"
    assert plan.conflicts == ()
    assert plan.auto_woven == ()


def test_override_cleared_when_source_changes():
    res = _resource(policy=MergePolicy.COOPERATIVE, desired="high")
    live = {"effort": "drifted"}
    store = FakeStore(
        fingerprints={_key(res, "/effort"): _fingerprint("low")},
        overrides={
            _key(res, "/effort"): {
                # Override was recorded for a DIFFERENT desired value.
                "source_field_fingerprint": _fingerprint("stale-desired"),
                "observed_value": "drifted",
            }
        },
    )
    plan = plan_resource(res, live, store)
    assert _action(plan).kind == "auto_weave"
    assert "/effort" in plan.auto_woven


# ── extract_field tests ───────────────────────────────────────────────────────

def test_extract_field_nested_path():
    assert extract_field({"a": {"b": 1}}, "/a/b") == 1


def test_extract_field_missing_segment():
    assert extract_field({}, "/x/y") is None


def test_extract_field_root_pointer():
    doc = {"a": 1}
    assert extract_field(doc, "") == doc


def test_extract_field_deep_provider_path():
    cfg = {"models": {"providers": {"lmstudio-mac": {"baseUrl": "http://host:1234"}}}}
    assert extract_field(cfg, "/models/providers/lmstudio-mac/baseUrl") == "http://host:1234"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
