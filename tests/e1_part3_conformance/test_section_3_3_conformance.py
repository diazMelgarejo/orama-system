"""Conformance tests for E1 C2 Part 3 Section 3.3 against the reference model.

Covers packet item 3: cold bootstrap, checkpoint acknowledgement, repeated pruning, identical
retry, conflicting retry and quarantine, clearing, lower-floor rejection, crash safety.
"""
import sqlite3
from typing import Any

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .anchor_model import (
    ZERO_DIGEST,
    AnchorConflict,
    AnchorConsumer,
    AnchorQuarantineClearRefused,
    AnchorRefusal,
    Event,
    HotStore,
    Row,
    TrustedKeys,
    event_digest,
)

ISSUER = "issuer-a"
KEY_ID = "key-1"
PREFIX = b"phylax-issuer-event-v1\x00"
_PRIV = Ed25519PrivateKey.generate()
_PUB = _PRIV.public_key()
_OTHER = Ed25519PrivateKey.generate()


def verifier(key: Ed25519PublicKey, digest: str, signature: str) -> bool:
    """Stand-in Ed25519 check over the event prefix and the hex digest."""
    try:
        key.verify(bytes.fromhex(signature), PREFIX + digest.encode())
        return True
    except InvalidSignature:
        return False


def make_event(
    version: int,
    previous: str = ZERO_DIGEST,
    kind: str = "finalization",
    signer: Ed25519PrivateKey = _PRIV,
    body: dict[str, Any] | None = None,
) -> Event:
    """Build a signed event at ``version`` chained to ``previous``."""
    event: Event = {
        "body": body or {"finalization_id": f"f{version}"},
        "kind": kind,
        "previous_event_digest": previous,
        "version": version,
        "issuer_key_id": KEY_ID,
    }
    event["event_digest"] = event_digest(event)
    event["signature"] = signer.sign(PREFIX + event["event_digest"].encode()).hex()
    return event


def chain(start: int, end: int, anchor_previous: str = "a" * 64) -> list[Event]:
    """Build a contiguous signed chain of events from ``start`` to ``end`` inclusive."""
    events, previous = [], anchor_previous
    for v in range(start, end + 1):
        e = make_event(v, previous)
        events.append(e)
        previous = e["event_digest"]
    return events


TRUSTED: TrustedKeys = {ISSUER: {KEY_ID: _PUB}}


@pytest.fixture
def consumer() -> AnchorConsumer:
    """A fresh in-memory reference consumer."""
    return AnchorConsumer()


def bootstrap(
    c: AnchorConsumer, event: Event, issuer: str = ISSUER, trusted: TrustedKeys = TRUSTED
) -> None:
    """Bootstrap ``event`` as the anchor with the test verifier and trust roots."""
    c.bootstrap_anchor(issuer, event, verifier, trusted)


def persisted(c: AnchorConsumer, issuer: str = ISSUER) -> Row:
    """Return the persisted anchor record, failing the test if none exists."""
    rec = c.record(issuer)
    assert rec is not None
    return rec


def ack(
    c: AnchorConsumer, event: Event, issuer: str = ISSUER, trusted: TrustedKeys = TRUSTED
) -> bool:
    """Acknowledge ``event`` with the same verifier and trust roots as bootstrap."""
    return c.acknowledge(issuer, event, verifier, trusted)


def test_cold_bootstrap_persists_identity_floor_and_base_atomically(consumer: AnchorConsumer) -> None:
    anchor = chain(5, 5)[0]

    bootstrap(consumer, anchor)

    rec = persisted(consumer)
    assert rec[:5] == (ISSUER, KEY_ID, 5, anchor["event_digest"], 5)
    assert rec[5:8] == (5, anchor["event_digest"], 5)  # base and acked_through
    assert rec[8] == 0


def test_bootstrap_at_n_gt_1_sets_acked_through_n_and_never_below(consumer: AnchorConsumer) -> None:
    bootstrap(consumer, chain(7, 7)[0])

    assert consumer.acked_through(ISSUER) == 7


def test_gap_does_not_advance_but_next_event_does(consumer: AnchorConsumer) -> None:
    events = chain(5, 8)
    bootstrap(consumer, events[0])

    assert ack(consumer, events[2]) is False  # gap at 6
    assert consumer.acked_through(ISSUER) == 5
    assert ack(consumer, events[1]) is True
    assert consumer.acked_through(ISSUER) == 6
    assert ack(consumer, events[2]) is True
    assert consumer.acked_through(ISSUER) == 7


def test_conflicting_event_above_anchor_does_not_advance(consumer: AnchorConsumer) -> None:
    events = chain(5, 6)
    bootstrap(consumer, events[0])
    forged = make_event(6, previous="b" * 64)

    assert ack(consumer, forged) is False
    assert consumer.acked_through(ISSUER) == 5


def test_unverifiable_next_event_does_not_advance(consumer: AnchorConsumer) -> None:
    events = chain(5, 6)
    bootstrap(consumer, events[0])
    wrong_signer = make_event(6, previous=events[0]["event_digest"], signer=_OTHER)
    stale_digest = dict(events[1], body={"finalization_id": "tampered"})

    assert ack(consumer, wrong_signer) is False
    assert ack(consumer, events[1], trusted={ISSUER: {}}) is False
    assert ack(consumer, stale_digest) is False
    assert consumer.acked_through(ISSUER) == 5
    assert ack(consumer, events[1]) is True
    assert consumer.acked_through(ISSUER) == 6


def test_digest_mismatch_is_plain_refusal_and_persists_nothing(consumer: AnchorConsumer) -> None:
    anchor = chain(5, 5)[0]
    anchor["event_digest"] = "0" * 64

    with pytest.raises(AnchorRefusal, match="digest_mismatch"):
        bootstrap(consumer, anchor)

    assert consumer.record(ISSUER) is None


def test_signature_over_caller_digest_alone_is_insufficient(consumer: AnchorConsumer) -> None:
    anchor = chain(5, 5)[0]
    anchor["body"] = {"finalization_id": "tampered"}
    anchor["event_digest"] = event_digest(anchor)  # digest is consistent; only the signature is stale

    with pytest.raises(AnchorRefusal, match="bad_signature"):
        bootstrap(consumer, anchor)

    assert consumer.record(ISSUER) is None


def test_key_supplied_only_by_event_is_not_trusted(consumer: AnchorConsumer) -> None:
    anchor = chain(5, 5)[0]

    with pytest.raises(AnchorRefusal, match="untrusted_key"):
        bootstrap(consumer, anchor, trusted={ISSUER: {}})
    with pytest.raises(AnchorRefusal, match="untrusted_key"):
        bootstrap(consumer, anchor, trusted={"other-issuer": {KEY_ID: _PUB}})

    assert consumer.record(ISSUER) is None


def test_bad_signature_is_plain_refusal(consumer: AnchorConsumer) -> None:
    anchor = make_event(5, "a" * 64, signer=_OTHER)

    with pytest.raises(AnchorRefusal, match="bad_signature"):
        bootstrap(consumer, anchor)

    assert consumer.record(ISSUER) is None


def test_identical_retry_is_noop_and_keeps_acked_through(consumer: AnchorConsumer) -> None:
    events = chain(5, 7)
    bootstrap(consumer, events[0])
    ack(consumer, events[1])
    ack(consumer, events[2])

    bootstrap(consumer, events[0])

    assert consumer.acked_through(ISSUER) == 7
    assert persisted(consumer)[8] == 0


def test_conflicting_retry_refuses_quarantines_and_keeps_persisted_values(consumer: AnchorConsumer) -> None:
    original = chain(5, 5)[0]
    bootstrap(consumer, original)
    before = persisted(consumer)[:8]
    conflicting = make_event(5, "c" * 64)

    with pytest.raises(AnchorConflict):
        bootstrap(consumer, conflicting)

    after = persisted(consumer)
    assert after[:8] == before
    assert after[8] == 1


def test_lower_version_retry_cannot_lower_floor(consumer: AnchorConsumer) -> None:
    bootstrap(consumer, chain(9, 9)[0])

    with pytest.raises(AnchorConflict):
        bootstrap(consumer, chain(3, 3)[0])

    assert persisted(consumer)[4] == 9


def test_quarantine_blocks_that_issuer_only_and_writes_no_authority(consumer: AnchorConsumer) -> None:
    bootstrap(consumer, chain(5, 5)[0])
    other_events = chain(2, 2)
    other_trusted = {**TRUSTED, "issuer-b": {KEY_ID: _PUB}}
    consumer.bootstrap_anchor("issuer-b", other_events[0], verifier, other_trusted)
    with pytest.raises(AnchorConflict):
        bootstrap(consumer, make_event(5, "c" * 64))
    consumer.add_reservation("r-a")
    consumer.add_reservation("r-b")

    assert consumer.authorize(ISSUER, "r-a", 99) == "anchor_quarantined"
    assert consumer.reservation_consumed("r-a") is False
    assert consumer.authority_writes() == 0
    assert consumer.authorize("issuer-b", "r-b", 99) == "authorized"


def test_matching_later_bootstrap_does_not_clear_quarantine(consumer: AnchorConsumer) -> None:
    original = chain(5, 5)[0]
    bootstrap(consumer, original)
    with pytest.raises(AnchorConflict):
        bootstrap(consumer, make_event(5, "c" * 64))

    bootstrap(consumer, original)  # identical to persisted: no-op

    assert persisted(consumer)[8] == 1


def test_quarantine_survives_restart_semantics_because_flag_is_in_record(consumer: AnchorConsumer) -> None:
    bootstrap(consumer, chain(5, 5)[0])
    with pytest.raises(AnchorConflict):
        bootstrap(consumer, make_event(5, "c" * 64))

    assert consumer.db.execute("SELECT quarantined FROM anchor").fetchone()[0] == 1


@pytest.mark.parametrize("operator_ref,evidence", [("", "ev"), ("  ", "ev"), (None, "ev"), ("op", ""), ("op", "  ")])
def test_clear_requires_operator_reference_and_evidence(
    consumer: AnchorConsumer, operator_ref: str | None, evidence: str
) -> None:
    bootstrap(consumer, chain(5, 5)[0])
    with pytest.raises(AnchorConflict):
        bootstrap(consumer, make_event(5, "c" * 64))

    with pytest.raises(AnchorQuarantineClearRefused):
        consumer.clear_anchor_quarantine(ISSUER, operator_ref=operator_ref, evidence=evidence, ts="t")

    assert persisted(consumer)[8] == 1
    assert consumer.clear_log() == []


def test_clear_needs_existing_quarantine(consumer: AnchorConsumer) -> None:
    bootstrap(consumer, chain(5, 5)[0])

    with pytest.raises(AnchorQuarantineClearRefused):
        consumer.clear_anchor_quarantine(ISSUER, operator_ref="op", evidence="ev", ts="t")


def test_audited_clear_appends_log_and_never_lowers_floor(consumer: AnchorConsumer) -> None:
    bootstrap(consumer, chain(5, 5)[0])
    with pytest.raises(AnchorConflict):
        bootstrap(consumer, make_event(5, "c" * 64))

    consumer.clear_anchor_quarantine(ISSUER, operator_ref="op-1", evidence="signed note", ts="t1")

    rec = persisted(consumer)
    assert rec[8] == 0 and rec[4] == 5
    log = consumer.clear_log()
    assert len(log) == 1 and log[0][5] == "op-1" and log[0][4] == "signed note"


def test_lower_floor_permit_refused_without_authority_write_and_reservation_kept(consumer: AnchorConsumer) -> None:
    bootstrap(consumer, chain(5, 5)[0])
    consumer.add_reservation("r1")

    assert consumer.authorize(ISSUER, "r1", 4) == "anchor_floor.permit_below_floor"

    assert consumer.reservation_consumed("r1") is False
    assert consumer.authority_writes() == 0
    assert consumer.authorize(ISSUER, "r1", 5) == "authorized"  # same reservation, fresh permit


def test_permit_at_or_above_floor_is_authorized(consumer: AnchorConsumer) -> None:
    bootstrap(consumer, chain(5, 5)[0])
    consumer.add_reservation("r1")
    consumer.add_reservation("r2")

    assert consumer.authorize(ISSUER, "r1", 5) == "authorized"
    assert consumer.authorize(ISSUER, "r2", 50) == "authorized"


def test_issuer_without_anchor_has_no_floor(consumer: AnchorConsumer) -> None:
    consumer.add_reservation("r1")

    assert consumer.authorize("never-bootstrapped", "r1", 0) == "authorized"


def test_refusal_reason_is_consumer_local_not_a_wire_code(consumer: AnchorConsumer) -> None:
    bootstrap(consumer, chain(5, 5)[0])
    consumer.add_reservation("r1")

    reason = consumer.authorize(ISSUER, "r1", 1)

    assert reason == "anchor_floor.permit_below_floor"


def test_crash_between_anchor_insert_and_ack_audit_leaves_nothing() -> None:
    crashing = AnchorConsumer(fail_after_anchor_insert=True)

    with pytest.raises(RuntimeError):
        crashing.bootstrap_anchor(ISSUER, chain(5, 5)[0], verifier, TRUSTED)

    assert crashing.record(ISSUER) is None
    assert crashing.db.execute("SELECT COUNT(*) FROM ack").fetchone()[0] == 0


def test_repeated_pruning_leaves_only_latest_anchor_hot_and_archives_former() -> None:
    store = HotStore(range(1, 21))

    store.prune_to(5)
    assert store.anchor == 5 and 5 not in store.archive and {1, 2, 3, 4} <= store.archive
    store.prune_to(12)

    assert store.anchor == 12
    assert 5 in store.archive and 12 not in store.archive
    assert {v for v in store.hot if v <= 12} == {12}  # only the new anchor remains hot
    assert store.archive == set(range(1, 12))


def test_repeated_bootstrap_with_different_key_identity_quarantines(consumer: AnchorConsumer) -> None:
    bootstrap(consumer, chain(5, 5)[0])
    same_event_other_key = chain(5, 5)[0]
    same_event_other_key["issuer_key_id"] = "key-2"
    trusted = {ISSUER: {KEY_ID: _PUB, "key-2": _PUB}}

    with pytest.raises(AnchorConflict):
        bootstrap(consumer, same_event_other_key, trusted=trusted)

    assert persisted(consumer)[8] == 1 and persisted(consumer)[1] == KEY_ID


def test_read_only_inspection_stays_possible_under_quarantine(consumer: AnchorConsumer) -> None:
    events = chain(5, 6)
    bootstrap(consumer, events[0])
    ack(consumer, events[1])
    with pytest.raises(AnchorConflict):
        bootstrap(consumer, make_event(5, "c" * 64))

    assert consumer.record(ISSUER) is not None
    assert consumer.acked_through(ISSUER) == 6


def test_clear_log_rows_cannot_be_rewritten_or_deleted(consumer: AnchorConsumer) -> None:
    bootstrap(consumer, chain(5, 5)[0])
    with pytest.raises(AnchorConflict):
        bootstrap(consumer, make_event(5, "c" * 64))
    consumer.clear_anchor_quarantine(ISSUER, operator_ref="op", evidence="ev", ts="t")

    with pytest.raises(sqlite3.DatabaseError):
        consumer.db.execute("UPDATE clear_log SET evidence='x'")
    with pytest.raises(sqlite3.DatabaseError):
        consumer.db.execute("DELETE FROM clear_log")
    assert len(consumer.clear_log()) == 1


def test_events_below_the_anchor_are_never_acknowledged(consumer: AnchorConsumer) -> None:
    bootstrap(consumer, chain(5, 5)[0])
    below = make_event(4, "d" * 64)

    assert ack(consumer, below) is False
    assert consumer.acked_through(ISSUER) == 5
    assert consumer.db.execute("SELECT COUNT(*) FROM ack WHERE version<5").fetchone()[0] == 0
