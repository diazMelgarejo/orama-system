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
