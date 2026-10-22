"""Executable reference model of E1 C2 Part 3 Section 3.3 (test-only, not product code).

This is a minimal sqlite model of the consumer anchor-floor invariant, written from the
ratified text so the conformance tests have something to execute. It is NOT the Oramasys
implementation and authorizes none: no serving, emission, pin promotion or activation.
The same tests are meant to be pointed at the real consumer store once it exists.

Signing note: the tests' signer is a STAND-IN (pure Ed25519 via ``cryptography``). The real
event scheme is Ed25519ph over ``phylax-issuer-event-v1\\x00`` + the 64 hex digest characters;
it is verified against Phylax-signed vectors in Oramasys
``src/tests/test_dispatch_event_ed25519ph.py``, not here.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable, Iterable, Mapping
from typing import Any

ZERO_DIGEST = "0" * 64

Event = dict[str, Any]
"""A signed issuer event: body, kind, previous_event_digest, version, key id, digest, signature."""
Verifier = Callable[[Any, str, str], bool]
"""``verifier(public_key, event_digest, signature_hex)`` returns whether the signature holds."""
TrustedKeys = Mapping[str, Mapping[str, Any]]
"""Consumer-held trust roots: issuer id to key id to public key (never taken from the event)."""
Row = tuple[Any, ...]


class AnchorRefusal(Exception):
    """Plain refusal: nothing is persisted."""


class AnchorConflict(AnchorRefusal):
    """Repeated bootstrap differs from the persisted record: quarantine is retained."""


class AnchorQuarantineClearRefused(Exception):
    pass


def event_digest(event: Event) -> str:
    """SHA-256 of the canonical JSON of exactly body, kind, previous_event_digest, version."""
    preimage = {k: event[k] for k in ("body", "kind", "previous_event_digest", "version")}
    raw = json.dumps(preimage, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AnchorConsumer:
    def __init__(self, fail_after_anchor_insert: bool = False) -> None:
        self._fail_after_anchor_insert = fail_after_anchor_insert
        self.db = sqlite3.connect(":memory:", isolation_level=None)
        self.db.executescript(
            """
            CREATE TABLE anchor(issuer_id TEXT PRIMARY KEY, key_id TEXT NOT NULL,
              version INTEGER NOT NULL, digest TEXT NOT NULL, anchor_floor INTEGER NOT NULL,
              base_version INTEGER NOT NULL, base_digest TEXT NOT NULL,
              acked_through INTEGER NOT NULL, quarantined INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE ack(issuer_id TEXT, version INTEGER, digest TEXT,
              PRIMARY KEY(issuer_id, version));
            CREATE TABLE quarantine_evidence(issuer_id TEXT, conflicting TEXT);
            CREATE TABLE clear_log(id INTEGER PRIMARY KEY AUTOINCREMENT, issuer_id TEXT,
              previous TEXT, accepted TEXT, evidence TEXT, operator_ref TEXT, ts TEXT);
            CREATE TRIGGER clear_log_no_update BEFORE UPDATE ON clear_log
              BEGIN SELECT RAISE(ABORT, 'append-only'); END;
            CREATE TRIGGER clear_log_no_delete BEFORE DELETE ON clear_log
              BEGIN SELECT RAISE(ABORT, 'append-only'); END;
            CREATE TABLE reservation(reservation_id TEXT PRIMARY KEY, consumed INTEGER NOT NULL);
            CREATE TABLE authority_write(issuer_id TEXT, reservation_id TEXT);
            """
        )

    @staticmethod
    def _verified_digest(
        issuer_id: str, event: Event, verifier: Verifier, trusted_keys: TrustedKeys
    ) -> str:
        """Return the recomputed digest of a verified event, or raise the refusal reason.

        The one definition of "verified" for both bootstrap and acknowledgement: the digest is
        recomputed (a signature over a caller-supplied digest alone is insufficient), the key must
        be trusted for this issuer by the consumer, and the signature must hold over the digest.
        """
        digest = event_digest(event)
        if digest != event.get("event_digest"):
            raise AnchorRefusal("digest_mismatch")
        key = trusted_keys.get(issuer_id, {}).get(event.get("issuer_key_id", ""))
        if key is None:
            raise AnchorRefusal("untrusted_key")
        if not verifier(key, digest, event.get("signature", "")):
            raise AnchorRefusal("bad_signature")
        return digest

    # --- Section 3.3 item 1: bootstrap_anchor -------------------------------------------
    def bootstrap_anchor(
        self, issuer_id: str, anchor_event: Event, verifier: Verifier, trusted_keys: TrustedKeys
    ) -> None:
        """Persist the verified anchor atomically; a differing repeat quarantines the issuer."""
        digest = self._verified_digest(issuer_id, anchor_event, verifier, trusted_keys)
        version = anchor_event["version"]
        record = (issuer_id, anchor_event["issuer_key_id"], version, digest, version)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                "SELECT key_id, version, digest, anchor_floor FROM anchor WHERE issuer_id=?",
                (issuer_id,),
            ).fetchone()
            if row is None:
                self.db.execute(
                    "INSERT INTO anchor VALUES(?,?,?,?,?,?,?,?,0)",
                    (*record, version, digest, version),
                )
                if self._fail_after_anchor_insert:
                    raise RuntimeError("crash between anchor insert and ack audit")
                self.db.execute("INSERT INTO ack VALUES(?,?,?)", (issuer_id, version, digest))
                self.db.execute("COMMIT")
                return
            if row == (record[1], version, digest, version):
                self.db.execute("COMMIT")  # identical repeat: no-op
                return
            self.db.execute("UPDATE anchor SET quarantined=1 WHERE issuer_id=?", (issuer_id,))
            self.db.execute(
                "INSERT INTO quarantine_evidence VALUES(?,?)",
                (issuer_id, json.dumps(anchor_event, sort_keys=True)),
            )
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        raise AnchorConflict("conflicting_anchor")

    # --- checkpoint-aware acknowledgement ------------------------------------------------
    def acknowledge(
        self, issuer_id: str, event: Event, verifier: Verifier, trusted_keys: TrustedKeys
    ) -> bool:
        """Acknowledge a verified event; advance acked_through only without a gap.

        Section 3.3: an event at ``acked_through + 1`` advances it only after verification, so an
        unverifiable event (digest, key or signature) is refused exactly like a gap or a fork.
        """
        row = self.db.execute(
            "SELECT acked_through FROM anchor WHERE issuer_id=?", (issuer_id,)
        ).fetchone()
        if row is None:
            return False
        acked = row[0]
        prev = self.db.execute(
            "SELECT digest FROM ack WHERE issuer_id=? AND version=?", (issuer_id, acked)
        ).fetchone()
        if event["version"] != acked + 1 or event["previous_event_digest"] != prev[0]:
            return False
        try:
            digest = self._verified_digest(issuer_id, event, verifier, trusted_keys)
        except AnchorRefusal:
            return False
        self.db.execute("INSERT INTO ack VALUES(?,?,?)", (issuer_id, event["version"], digest))
        self.db.execute(
            "UPDATE anchor SET acked_through=? WHERE issuer_id=?", (event["version"], issuer_id)
        )
        return True

    def acked_through(self, issuer_id: str) -> int | None:
        row = self.db.execute(
            "SELECT acked_through FROM anchor WHERE issuer_id=?", (issuer_id,)
        ).fetchone()
        return row[0] if row else None

    def record(self, issuer_id: str) -> Row | None:
        row: Row | None = self.db.execute(
            "SELECT * FROM anchor WHERE issuer_id=?", (issuer_id,)
        ).fetchone()
        return row

    # --- Section 3.3 item 2: anchor-floor gate and quarantine block -----------------------
    def add_reservation(self, reservation_id: str) -> None:
        self.db.execute("INSERT INTO reservation VALUES(?,0)", (reservation_id,))

    def reservation_consumed(self, reservation_id: str) -> bool:
        return bool(
            self.db.execute(
                "SELECT consumed FROM reservation WHERE reservation_id=?", (reservation_id,)
            ).fetchone()[0]
        )

    def authorize(self, issuer_id: str, reservation_id: str, revocation_version: int) -> str:
        """Return 'authorized' or a consumer-local refusal reason; refusals write nothing."""
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                "SELECT anchor_floor, quarantined FROM anchor WHERE issuer_id=?", (issuer_id,)
            ).fetchone()
            if row is not None and row[1]:
                self.db.execute("ROLLBACK")
                return "anchor_quarantined"
            if row is not None and revocation_version < row[0]:
                self.db.execute("ROLLBACK")
                return "anchor_floor.permit_below_floor"
            self.db.execute("UPDATE reservation SET consumed=1 WHERE reservation_id=?", (reservation_id,))
            self.db.execute("INSERT INTO authority_write VALUES(?,?)", (issuer_id, reservation_id))
            self.db.execute("COMMIT")
            return "authorized"
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def authority_writes(self) -> int:
        return int(self.db.execute("SELECT COUNT(*) FROM authority_write").fetchone()[0])

    # --- clear_anchor_quarantine ----------------------------------------------------------
    def clear_anchor_quarantine(
        self, issuer_id: str, *, operator_ref: str | None, evidence: str | None, ts: str
    ) -> None:
        if not (operator_ref or "").strip():
            raise AnchorQuarantineClearRefused("operator_authority_missing")
        if not (evidence or "").strip():
            raise AnchorQuarantineClearRefused("evidence_missing")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                "SELECT quarantined FROM anchor WHERE issuer_id=?", (issuer_id,)
            ).fetchone()
            if row is None or not row[0]:
                raise AnchorQuarantineClearRefused("no_quarantine")
            record = json.dumps(self.record(issuer_id))
            self.db.execute(
                "INSERT INTO clear_log(issuer_id, previous, accepted, evidence, operator_ref, ts)"
                " VALUES(?,?,?,?,?,?)",
                (issuer_id, record, record, evidence, operator_ref, ts),
            )
            self.db.execute("UPDATE anchor SET quarantined=0 WHERE issuer_id=?", (issuer_id,))
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def clear_log(self) -> list[Row]:
        return self.db.execute("SELECT * FROM clear_log").fetchall()


class HotStore:
    """Section 3.2 rule 3: at most one retained boundary event hot; former anchors archived."""

    def __init__(self, versions: Iterable[int]) -> None:
        self.hot = set(versions)
        self.archive: set[int] = set()
        self.anchor: int | None = None

    def prune_to(self, boundary: int) -> None:
        moving = {v for v in self.hot if v < boundary}
        if self.anchor is not None and self.anchor < boundary:
            moving.add(self.anchor)
        self.archive |= moving
        self.hot -= moving
        self.anchor = boundary
