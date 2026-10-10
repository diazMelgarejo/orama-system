# P0 closure — Core pin promotion ACTIVATED (2026-10-10)

State machine outcome: STAGED, QUALIFIED, CANONICAL, **ACTIVATED**. Evidence is in
[receipt 4](P0-SUCCESSOR-EVIDENCE-RECEIPT-4-2026-10-10.md).

- Oramasys `main` pins Core `4d217f6b9e94e36554a9427198b8c2c4b7febc47` and verifies a
  clean non-editable install through PEP 610 `direct_url.json`.
- The six-cell manifest (profile by Python 3.11/3.12) and result-file gate run on every
  change; all eight checks passed at the merge commit.
- Orama and Oramasys registry digests match main to main.
- Rollback: the previous pair stays reachable in history; revert the pin commit to return.

Open operator item: branch protection requiring the eight checks. The next step is the
Perpetua-Tools memory correction; T1 stays gated until the operator opens it.
