"""Executable reference model of E1 C2 Part 3 Section 3.3 (test-only, not product code).

This is a minimal sqlite model of the consumer anchor-floor invariant, written from the
ratified text so the conformance tests have something to execute. It is NOT the Oramasys
implementation and authorizes none: no serving, emission, pin promotion or activation.
The same tests are meant to be pointed at the real consumer store once it exists.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3

ZERO_DIGEST = "0" * 64


class AnchorRefusal(Exception):
    """Plain refusal: nothing is persisted."""


class AnchorConflict(AnchorRefusal):
    """Repeated bootstrap differs from the persisted record: quarantine is retained."""


class AnchorQuarantineClearRefused(Exception):
    pass


def event_digest(event: dict) -> str:
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

    # --- Section 3.3 item 1: bootstrap_anchor -------------------------------------------
    def bootstrap_anchor(self, issuer_id, anchor_event, verifier, trusted_keys) -> None:
        digest = event_digest(anchor_event)
        if digest != anchor_event.get("event_digest"):
            raise AnchorRefusal("digest_mismatch")
        key = trusted_keys.get(issuer_id, {}).get(anchor_event.get("issuer_key_id"))
        if key is None:
            raise AnchorRefusal("untrusted_key")
        if not verifier(key, digest, anchor_event["signature"]):
            raise AnchorRefusal("bad_signature")
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
    def acknowledge(self, issuer_id, event) -> bool:
        """Acknowledge a verified event; advance acked_through only without a gap."""
        row = self.db.execute(
            "SELECT acked_through FROM anchor WHERE issuer_id=?", (issuer_id,)
        ).fetchone()
        if row is None:
            return False
        acked = row[0]
        prev = self.db.execute(
            "SELECT digest FROM ack WHERE issuer_id=? AND version=?", (issuer_id, acked)
        ).fetchone()
        digest = event_digest(event)
        if (
            event["version"] != acked + 1
            or event["previous_event_digest"] != prev[0]
            or digest != event.get("event_digest")
        ):
            return False
        self.db.execute("INSERT INTO ack VALUES(?,?,?)", (issuer_id, event["version"], digest))
        self.db.execute(
            "UPDATE anchor SET acked_through=? WHERE issuer_id=?", (event["version"], issuer_id)
        )
        return True

    def acked_through(self, issuer_id) -> int | None:
        row = self.db.execute(
            "SELECT acked_through FROM anchor WHERE issuer_id=?", (issuer_id,)
        ).fetchone()
        return row[0] if row else None

    def record(self, issuer_id):
        return self.db.execute("SELECT * FROM anchor WHERE issuer_id=?", (issuer_id,)).fetchone()

    # --- Section 3.3 item 2: anchor-floor gate and quarantine block -----------------------
    def add_reservation(self, reservation_id) -> None:
        self.db.execute("INSERT INTO reservation VALUES(?,0)", (reservation_id,))

    def reservation_consumed(self, reservation_id) -> bool:
        return bool(
            self.db.execute(
                "SELECT consumed FROM reservation WHERE reservation_id=?", (reservation_id,)
            ).fetchone()[0]
        )

    def authorize(self, issuer_id, reservation_id, revocation_version) -> str:
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
        return self.db.execute("SELECT COUNT(*) FROM authority_write").fetchone()[0]

    # --- clear_anchor_quarantine ----------------------------------------------------------
    def clear_anchor_quarantine(self, issuer_id, *, operator_ref, evidence, ts) -> None:
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

    def clear_log(self):
        return self.db.execute("SELECT * FROM clear_log").fetchall()


class HotStore:
    """Section 3.2 rule 3: at most one retained boundary event hot; former anchors archived."""

    def __init__(self, versions) -> None:
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
