# LAN peer TLS trust and outbox reconciliation

Operator reference for the peer portal link between the two hosts. Commands
below are subcommands of `scripts/lan_peer_assign.py`.

## Evidence levels

Do not call a peer file "delivered" on weaker evidence than the level that
proves it.

| Level | What it proves | What it does not prove |
| --- | --- | --- |
| TLS health 200 | The peer answers over verified TLS | That the peer accepts your token |
| Protected 401 | The endpoint exists and enforces auth | That your token is accepted |
| Authenticated receipt | An authenticated request over verified https returned `ok:true`, and the receiver independently reports the file in its own inbox | Nothing further; this is the bar for "delivered" |

A 2xx without `ok:true`, or a success that did not travel over verified
https with a token, is recorded as `sent`, never `delivered`.

## Trust settings

- `PEER_CA_FILE` is a PEM bundle used only for peer portal calls (HTTP
  requests and the WebSocket check). Chain and hostname or IP SAN are fully
  verified. Nothing global is modified.
- `PEER_PINNED_FINGERPRINTS` is a comma list of SHA-256 leaf fingerprints.
  A matching leaf becomes the trust anchor for a full verified handshake.
- `SSL_CERT_FILE` is the process-wide fallback. It applies only when neither
  peer setting is present, through the default verified context. It never
  weakens a configured `PEER_CA_FILE`.
- Verification is never disabled. If verification fails, no token is sent.
- A bearer token is only ever sent over verified https. Over http the token
  is withheld and the call proceeds unauthenticated (`SECURITY_STOP`).

## Cross-platform body bytes and receipts (2026-11-04)

Operator-directed convention for Mac and Windows. Implementation and review
evidence belongs in the coordination record; do not claim every agent agreed
until each active lane has acknowledged it. This section adds a storage
guarantee without changing the peer-file JSON schema or TLS/auth policy.

### Body representation

- The peer-file API carries Unicode text in the JSON `body` field, not an
  arbitrary binary attachment. The exact body bytes are `body.encode("utf-8")`.
  Hash the decoded field's UTF-8 bytes, not the enclosing JSON serialization.
- Inbox and outbox body persistence MUST use binary writes. Reads used for
  delivery or redelivery MUST decode binary reads as strict UTF-8. Neither
  boundary translates LF/CRLF, strips whitespace, adds a final newline, or
  inserts/removes a BOM. Preserve an explicitly supplied U+FEFF too.
- New agent-authored text SHOULD use UTF-8 without BOM and LF. This authoring
  convention does not authorize silently rewriting an existing file.
- The CLI's source-file read has the same preservation rule. Shell command
  substitution and text-mode reads must not silently trim trailing newlines
  or normalize a source before dispatch.
- Metadata `bytes` counts encoded body bytes, not characters or JSON envelope
  bytes. For a successful new write it MUST equal the stored file size.
  Receipt `bytes` comes from the actual stored file. Do not rewrite legacy
  metadata merely to make those two counts agree.
- New sidecars record `bytes` and `sha256` of the stored body, and are written
  as UTF-8 JSON with LF and no BOM, including subsequent delivery-state updates.
  Integrity fields are derived by the writer, not supplied through caller extras.
  Receipts still recompute hashes from actual bytes: cached metadata is a
  write-time observation, not proof that a later file edit did not occur.

### Two separately labelled hashes

| Receipt field | Definition | Meaning |
| --- | --- | --- |
| `sha256` | SHA-256 of exact stored bytes | Exact byte identity |
| `sha256_lf` | Decode UTF-8, replace CRLF with LF only, encode UTF-8, SHA-256 | Legacy text equivalence across newline translation |

LF normalization does not remove a BOM, trim trailing newlines, or convert a
lone CR. New UTF-8 body writes should have equal sender/receiver raw hashes.
The existing receipt command's replacement decoding of malformed UTF-8 is
not lossless; `sha256_lf` is compatibility evidence only for valid UTF-8.
Always retain `sha256` as the exact-byte evidence.

For historical records, unequal raw hashes and equal LF-normalized hashes
support a newline-only difference. Label this `legacy newline-equivalent`,
not `byte-identical`. A mismatched normalized hash or unexplained byte delta
remains a collision or integrity investigation; never resolve it by overwriting.
Keep the original records and append the reconciliation evidence.

### Incident and verification

The operator's Windows receipt analysis for the Mac canary reported 905
received bytes and 916 stored bytes, eleven LF-to-CRLF expansions, and no BOM.
That explains the eleven-byte delta without making raw hashes equal. JSON can
preserve LF; the implicit Windows text-mode write was the translation boundary.
Agreement of the LF-normalized hashes must still be checked against the actual
receipt before recording equivalent content.

Windows' `win-coord-utf8-bytes-20261104.md` subsequently reported the raw
digest and LF-normalized digest for that legacy canary, confirmed the newline
translation boundary, and agreed to this convention. This is one Windows
response, not unanimous acknowledgement by every agent. Native Windows
qualification and a fresh receipt from the patched receiver remain gates.

Local receipt command (no credential or network access):

```text
lan_peer_assign.py receipt mac-canary-20261104T015511Z.md --json
```

Portable regression coverage: `tests/test_lan_peer_byte_contract.py` emulates
Windows text-mode writes and tests both stores, CRLF readback/redelivery,
trailing newlines, multibyte UTF-8, empty bodies, and BOM preservation. Native
Windows qualification remains a separate evidence item, not a claim inferred
from passing macOS tests. Existing legacy receipt and duplicate checks stay.

## Outbox states

| State | Meaning |
| --- | --- |
| `queued` | Not accepted by the peer (default; absent state reads as queued) |
| `sent` | Peer answered 2xx but without authenticated `ok:true`; kept and retried |
| `delivered` | Authenticated receipt, or operator-recorded evidence |
| `superseded` | Operator recorded that the item was replaced; never resent |

`delivered` and `superseded` are terminal: flush and resubmit skip them.
`outbox-status` is read-only.

## Duplicate safety

Before any send, flush and resubmit list the destination inbox
(authenticated when a token and verified https are available). If the same
remote filename is already there, nothing is sent:

- Authenticated listing and the listed size equals the body size (LF or CRLF
  line endings, since a Windows receiver translates newlines): the remote file
  is then fetched through the authenticated read path (GET
  /api/peer-inbox/NAME, verified https only) and its SHA-256 is compared with
  the local body (newlines normalized). Only an equal digest is marked
  `delivered`, with evidence "present in peer inbox listing; content sha256
  verified". These items are always kept in the outbox as evidence, regardless
  of `--keep-delivered`.
- Authenticated listing but the size differs, or the content differs or cannot
  be fetched or verified: a name collision. The item stays `queued` with
  last_error "same name present on peer with different or unverifiable
  content; operator must resolve", is not resent automatically, and needs
  `outbox-resolve` or `outbox-resubmit` with a new explicit remote filename.
  `outbox-status` shows `size_matches` and `content_verified`.
- Unauthenticated listing: marked `sent`, not resent.

If the listing cannot be fetched, nothing is sent and the item stays queued.
A failed attempt never removes the outbox file. A plain `flush-outbox` skips
any unresolved item whose last resubmit went to another destination (whatever
its state). `flush-outbox --only FILE` resends such an item to that last
approved destination, not the original address, and records history.

## Recording out-of-band evidence

```text
lan_peer_assign.py outbox-resolve --only FILE [--only FILE ...] \
  --state delivered|superseded --evidence "plain text"
```

- Makes no network call. Writes state, a UTC `resolved_at`, and the evidence
  into the item metadata.
- Evidence is control-character stripped and length limited. Text that looks
  like a credential is refused. No credential option exists.
- At least one explicit `--only` is required. Every name must match exactly
  one item or nothing is changed.

## Re-sending to an approved destination

```text
lan_peer_assign.py outbox-resubmit --only FILE [--only FILE ...] \
  --peer-ip HOST --portal-port PORT
```

- Sends the same body under the same remote filename.
- Original destination fields in the item are preserved. A `history` list
  records `from`, `to`, `at` and `result` for each attempt.
- Same transport rules as `drop`. Duplicate safety applies.
- Destination and items are always explicit.

## Rule: no bulk retarget

Never retarget the whole outbox at a new address. A changed address is not
proof that the old items belong there. Resubmit named items to a destination
you have approved, one decision at a time, and resolve items you can prove
are already delivered or replaced.

## Evidence flow: canary, receipt, then item by item

Before resolving or resubmitting anything, gather evidence in this order:

1. Canary: drop one small known file to the destination and confirm the
   authenticated listing shows it.
2. Receipt: on the receiving node run `lan_peer_assign.py receipt NAME [--json]`.
   It is local and read-only (no network, no tokens). It prints `filename`,
   `bytes`, `sha256` of the body exactly as stored, `sha256_lf` (the same
   LF-normalised hash `outbox-status` uses, so a CRLF/LF difference is
   explainable), `received_utc` and `host`. It exits 2 when the file is missing.
3. Only then act on individual outbox items with `outbox-resolve` or
   `outbox-resubmit`, one item at a time. Never a bulk retarget.
