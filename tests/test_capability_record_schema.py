"""Tests for the draft capability-record schema and the D0 receipt/freeze documents."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "schemas" / "capability-record.schema.json"
DOCS = [
    ROOT / "docs" / "v2" / "references" / "activation-readiness-baseline-2026-10-26.md",
    ROOT / "docs" / "v2" / "references" / "r0-r2-contract-freeze-2026-10-26.md",
]
BITS = ["serving", "effects", "transport", "continuation", "autonomous_settlement"]
DIGEST = "sha256:" + "0" * 64
IPV4 = re.compile(r"(?<![0-9A-Za-z.])(?:\d{1,3}\.){3}\d{1,3}(?![0-9A-Za-z])")


def _schema() -> dict[str, Any]:
    """Load the capability-record schema from disk."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _record() -> dict[str, Any]:
    """Return a valid all-false capability record."""
    return {
        "schema": "orama-capability-record/v1",
        "record_id": "rec-1",
        "issued_at": "2026-10-26T00:00:00Z",
        "issuer": "control-plane-test",
        "capabilities": {bit: False for bit in BITS},
        "binds": {"binary_digest": DIGEST, "config_digest": DIGEST},
        "signature": None,
    }


def _pre_dispatch_refusal_section(text: str) -> str:
    """Return the refusal contract without matching similar plan prose elsewhere."""
    heading = "### Pre-dispatch refusal record and replay"
    start = text.index(heading)
    end = text.index("\n## 5. Release 2 frozen items", start)
    return text[start:end]


def _type_ok(value: Any, name: str) -> bool:
    """Return whether value matches the JSON Schema primitive type name."""
    if name == "null":
        return value is None
    if name == "boolean":
        return isinstance(value, bool)
    if name == "string":
        return isinstance(value, str)
    if name == "object":
        return isinstance(value, dict)
    raise AssertionError(f"unsupported type in schema: {name}")


def _check(node: dict[str, Any], value: Any, errors: list[str], path: str = "$") -> None:
    """Minimal structural validator covering the keywords this schema uses."""
    if "const" in node and value != node["const"]:
        errors.append(f"{path}: const")
    if "type" in node:
        types = node["type"] if isinstance(node["type"], list) else [node["type"]]
        if not any(_type_ok(value, t) for t in types):
            errors.append(f"{path}: type")
            return
    if isinstance(value, str):
        if len(value) < node.get("minLength", 0):
            errors.append(f"{path}: minLength")
        if "pattern" in node and not re.search(node["pattern"], value):
            errors.append(f"{path}: pattern")
    if isinstance(value, dict) and "properties" in node:
        for key in node.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key}: required")
        if node.get("additionalProperties") is False:
            for key in value:
                if key not in node["properties"]:
                    errors.append(f"{path}.{key}: additional")
        for key, sub in node["properties"].items():
            if key in value:
                _check(sub, value[key], errors, f"{path}.{key}")


def _errors(record: Any) -> list[str]:
    """Return validation errors for record, cross-checked with jsonschema when installed."""
    errors: list[str] = []
    _check(_schema(), record, errors)
    try:
        import jsonschema  # optional cross-check; not a repo dependency
    except ImportError:
        return errors
    validator = jsonschema.Draft202012Validator(_schema())
    jerrors = list(validator.iter_errors(record))
    assert bool(jerrors) == bool(errors), (jerrors, errors)
    return errors


def test_schema_is_valid_json_with_draft_2020_12() -> None:
    """Schema declares draft 2020-12 and closes the capability bit set."""
    schema = _schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    caps = schema["properties"]["capabilities"]
    assert sorted(caps["required"]) == sorted(BITS)
    assert caps["additionalProperties"] is False
    assert all(caps["properties"][b] == {"type": "boolean"} for b in BITS)


def test_default_all_false_record_validates() -> None:
    """The default all-false record is valid."""
    assert _errors(_record()) == []


def test_signature_object_is_allowed_shape() -> None:
    """A signature object is accepted by shape."""
    record = _record()
    record["signature"] = {"alg": "test", "value": "x"}
    assert _errors(record) == []


@pytest.mark.parametrize("bit", BITS)
def test_missing_bit_fails(bit: str) -> None:
    """A record missing any capability bit is invalid."""
    record = _record()
    del record["capabilities"][bit]
    assert _errors(record)


@pytest.mark.parametrize("bit", BITS)
@pytest.mark.parametrize("bad", [0, 1, "false", None])
def test_non_bool_bit_fails(bit: str, bad: Any) -> None:
    """A non-boolean capability bit is invalid."""
    record = _record()
    record["capabilities"][bit] = bad
    assert _errors(record)


@pytest.mark.parametrize("where", ["top", "capabilities", "binds"])
def test_extra_key_fails(where: str) -> None:
    """Unknown keys are rejected at every level."""
    record = _record()
    target = record if where == "top" else record[where]
    target["extra"] = True
    assert _errors(record)


@pytest.mark.parametrize("field", ["schema", "record_id", "issued_at", "issuer", "binds",
                                   "signature", "capabilities"])
def test_missing_top_level_field_fails(field: str) -> None:
    """Every top-level field is required."""
    record = _record()
    del record[field]
    assert _errors(record)


@pytest.mark.parametrize("bad", ["sha256:abc", "sha256:" + "G" * 64, "md5:" + "0" * 64,
                                 "sha256:" + "0" * 65, "SHA256:" + "0" * 64])
def test_bad_digest_fails(bad: str) -> None:
    """Malformed digests are rejected for both bound digests."""
    for key in ("binary_digest", "config_digest"):
        record = copy.deepcopy(_record())
        record["binds"][key] = bad
        assert _errors(record)


def test_unknown_schema_and_bad_timestamp_fail() -> None:
    """An unknown schema id or a malformed timestamp is invalid."""
    record = _record()
    record["schema"] = "orama-capability-record/v2"
    assert _errors(record)
    record = _record()
    record["issued_at"] = "2026-10-26 00:00:00"
    assert _errors(record)


@pytest.mark.unit
def test_pre_dispatch_refusal_contract_preserves_e1_outcomes() -> None:
    """A pre-dispatch refusal is durable without becoming a fourth E1 outcome."""
    text = DOCS[1].read_text(encoding="utf-8")
    contract = " ".join(_pre_dispatch_refusal_section(text).split())

    assert "`authorization_refused` **disposition**, not an outcome value" in contract
    assert "`confirmed`, `failed`, and `unknown`" in contract
    for field in ("`attempt_id`", "`disposition`", "`refusal_code`", "`receipt_ref`", "`recorded_at`"):
        assert field in contract
    assert "existing `BEGIN IMMEDIATE` authorization transaction" in contract
    assert "It does not consume a use" in contract
    assert "An exact replay first looks up `attempt_id`" in contract
    assert '"<stored refusal_code>"' in contract
    assert '"<stored opaque receipt_ref>"' in contract


@pytest.mark.unit
def test_refusal_replay_body_nests_receipt_ref_inside_error() -> None:
    """The replay body places receipt_ref inside the error object, never beside it."""
    contract = _pre_dispatch_refusal_section(DOCS[1].read_text(encoding="utf-8"))
    match = re.search(r"```json\n(.+?)\n\s*```", contract, re.DOTALL)
    assert match
    body = json.loads(match.group(1).replace("<", "").replace(">", ""))
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "correlation_id", "receipt_ref"}


@pytest.mark.unit
def test_refusal_rules_cover_send_marker_and_in_doubt() -> None:
    """No terminal refusal after the send marker; in-doubt dispatch is a 503 with a receipt_ref."""
    contract = " ".join(_pre_dispatch_refusal_section(DOCS[1].read_text(encoding="utf-8")).split())
    assert "No terminal refusal after the send marker" in contract
    assert "no refusal record may be written" in contract
    assert "HTTP 503 `deny.verifier_unavailable` with its `receipt_ref`" in contract
    assert "never converted into a refusal record" in contract


@pytest.mark.unit
def test_public_error_section_fixes_statuses_and_unauthorized_rule() -> None:
    """Section 3 states the HTTP status table, the 401 rule and the in-doubt rule in the body."""
    text = DOCS[1].read_text(encoding="utf-8")
    start = text.index("## 3. Public error vocabulary")
    section = text[start : text.index("## 4. Terminal taxonomy mapping", start)]
    assert "| `deny.unauthorized_caller` | 401 |" in section
    assert "| `deny.malformed_grant` | 400 |" in section
    assert "`deny.revocation_stale`, `deny.verifier_unavailable` | 503 |" in section
    assert "HTTP 401 with `deny.unauthorized_caller`" in section
    flat = " ".join(section.split())
    assert "HTTP 503 with `deny.verifier_unavailable` and the opaque `receipt_ref`" in flat
    assert "`receipt_ref` is never a sibling of `error`" in section


@pytest.mark.unit
def test_lease_epoch_and_fencing_epoch_are_defined_and_distinct() -> None:
    """Both epochs are defined, kept apart, and every send goes through one shared helper."""
    text = DOCS[1].read_text(encoding="utf-8")
    start = text.index("## 5. Release 2 frozen items")
    section = " ".join(text[start : text.index("## 6. Out of scope", start)].split())
    assert "**Fencing epoch (defined).**" in section
    assert "**Lease epoch (defined, distinct).**" in section
    assert "neither epoch implies the other" in section
    assert "one shared helper that every send entry" in section
    assert "no second path sends" in section


def test_envelope_epoch_replay_and_refusal_audit_rules() -> None:
    """Envelope epoch is the fencing epoch; replay and audit-only reasons are stated once."""
    text = DOCS[1].read_text(encoding="utf-8")
    start = text.index("## 5. Release 2 frozen items")
    section = " ".join(text[start : text.index("## 6. Out of scope", start)].split())
    assert "The `epoch` field is the fencing epoch (distinct from the consumer lease epoch" in section
    assert "Replay of a settled successful send returns the stored receipt before any re-authorization" in section
    assert "lease check runs in the shared send-time helper inside the send transaction" in section
    assert "fails closed when no lease view is available" in section
    refusal = " ".join(_pre_dispatch_refusal_section(text).split())
    assert "may store the internal kind, rule or reason for audit only, and never exposes it" in refusal
    assert "exactly `disposition`, `refusal_code`, `receipt_ref` and `recorded_at`" in refusal
    assert "It stores no grant id, key id, target or payload." in refusal


def test_refusal_replay_binding_digest_and_existing_attempt_transition() -> None:
    """Refusal records persist binding_digest for replay check; existing attempts transition atomically."""
    text = DOCS[1].read_text(encoding="utf-8")
    refusal = " ".join(_pre_dispatch_refusal_section(text).split())
    assert "verifiable `binding_digest`" in refusal
    assert "compares the incoming request's bound identity against the stored `binding_digest`" in refusal
    assert "fails the binding digest check, is rejected as a conflict" in refusal
    assert "Existing unsent attempt blocked by revocation" in refusal
    assert 'atomically transitions the existing attempt to `disposition: "authorization_refused"`' in refusal
    assert "releases any held reservation, clears pending outbox intent" in refusal


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: p.name)
def test_docs_contain_no_ip_literals_or_workstation_paths(doc: Path) -> None:
    """Documents carry no IP literals or workstation paths."""
    text = doc.read_text(encoding="utf-8")
    assert not IPV4.findall(text)
    assert not re.search(r"[A-Za-z]:\\|/Users/|/home/", text)


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: p.name)
def test_docs_state_draft_and_no_activation(doc: Path) -> None:
    """Documents state draft status and no activation."""
    text = doc.read_text(encoding="utf-8")
    assert "ORAMA_GRANT_SERVING" in text
    assert "not" in text.split("\n\n", 2)[1].lower()
