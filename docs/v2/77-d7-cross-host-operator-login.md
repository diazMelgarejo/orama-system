# D7 - Cross-host operator login (design only)

> **Status:** design only. No code, provisioning, or migration in this change.
> **Repository standard:** additive -- [`46-repository-standard.md`](46-repository-standard.md).
> **Date:** 2026-11-27. **Scope:** one person, one login, across several hosts.
> **Parents:** docs 49, 50, 51, 61, 62, 70, 71. **Evidence:** Perpetua-Tools working memory
> `WIN_MAC_AUTH_RESTORATION_AND_60_DAY_RENEWAL_2026-11-17.md` and semantic memory
> `LAN_PEER_TLS_AUTH_CHAIN_AND_RENEWAL_V2_DOMAIN_KNOWLEDGE_2026-11-17.md`; every file name is
> quoted again in the tag map below.
> **Does not supersede** docs 45, 49, 50, 51, 61, 62, 70, 71. D23 in doc 45 still describes the
> live threat model: a single-operator LAN, not multi-principal. `[R70]`

## 0. Statement labels

Each line is `[P]` proposed here, `[U]` unverified, or `[Rxx]` read in the file mapped below:
R46 `46-repository-standard.md`; R49 `49-peer-mesh-auth-tls-v2-plan.md`; R50
`50-mesh-security-migration-ladder.md`; R51 `51-security-sentinel-orbit-passkey-mcp.md`; R61
`61-pt-coordination-principal-identity-design.md`; R62 `62-telos-phylax-authority-gate0-adr.md`;
R70 `70-portal-knowledge-hitl-development-ladder.md`; R71
`71-operator-provisioning-and-autonomous-tier-adr.md`; Rsem
`LAN_PEER_TLS_AUTH_CHAIN_AND_RENEWAL_V2_DOMAIN_KNOWLEDGE_2026-11-17.md`; Rmem
`WIN_MAC_AUTH_RESTORATION_AND_60_DAY_RENEWAL_2026-11-17.md`; Rmesh `orchestrator/mesh_auth.py`;
Rcpa `orchestrator/control_plane_auth.py`; Rspend `orchestrator/spend_gate.py`.

## 1. Goal

- One operator account works on every host, and a rebuilt host loses nothing. `[P]`
- Login proves a human is present, not that a token file was readable. `[P]`
- One per-user data key, wrapped per credential, never plaintext at rest. `[P]`
- Consequential actions (spend arming first) need a server-minted, short-TTL,
  exact-preview-bound human-presence proof. `[P]`
- The bearer mesh keeps working untouched and nobody is forced to migrate: it "must never
  stop working because of an auth change". `[R49]`
- Non-goal: agent-to-agent identity. That is doc 61's subject and stays separate. `[R61]` `[P]`

## 2. What exists today: machine identity only

**2.1 The 3-layer peer chain.** Three independent gates: TLS chain to a pinned CA, TLS
hostname against the leaf **SAN**, then HTTP bearer -- "A fix at one says nothing about the
others." `[Rsem]` Layer 2 dials the raw IP, so the leaf needs the IP SAN ("CN-only certs can
NEVER match an IP connection", RFC 6125); layer 3 sends `Authorization: Bearer` only after
"layers 1+2 passed (RFC 6750 5.3)". Transport proves a host, never a person. `[Rsem]` `[P]`

**2.2 Shared gossip secret.** `gossip_shared_secret()` returns `GOSSIP_SHARED_SECRET`;
`require_gossip_auth()` answers 503 when `PT_BIND_LAN=1` and unset, and 403 on a mismatched
`x-gossip-secret`. `[Rmesh]` It names a machine, not a person. `[P]`

**2.3 Shared control-plane token.** `ENV_TOKEN` is `ORAMA_CONTROL_PLANE_TOKEN`, with `..._LOCAL`,
`..._PEER`, `PT_...` and a persisted `.state/control_plane_token` served by
`pt_lane_token_candidates()` / `orama_lane_token_candidates()`. `[Rcpa]` Operationally "ONE
shared control-plane token, both directions", 43 characters, and inbound validation and
outbound bearer must match on both hosts. `[Rsem]` `[Rmem]` Its identity semantics are already
documented as absent: "The shared control-plane bearer identifies one local-operator
capability, not distinct agents. All callers using it share the Level 0 quota bucket." `[R71]`

**2.4 One LAN certificate authority, key custody on one host.** "One CA, one pin, one token";
"CA private keys never travel"; peers send CSRs and the CA-holding host signs 60-day leaves,
though there is "no CSR path in `orchestrator/lan_control_plane_pki.py`; CSR signing is an
operator procedure". `[Rsem]` `ca-pin.json` pins the CA DER sha256 at first start and refuses a
different CA (exit 3), but there is "no CRL/OCSP path", so "a compromised old leaf that still
chains to the pinned CA remains trusted until it expires". Two same-subject CAs once coexisted
and produced "pin X matches nothing"; believing the first available pin cost a whole
restoration session. Inventory first. `[Rsem]` `[Rmem]`

**2.5 What is missing.** No user record, credential registry, or per-user key in the paths read:
a search for any principal/session/auth concept "found zero matches" in the coordination CLI.
`[R61]` The spend gate's human gate is a static file -- `_attestation()` reads a JSON record and
`preflight()` refuses with `attestation-required` -- and a same-user process can write it, so it
cannot tell a human from an agent. `[Rspend]` `[P]` `GOSSIP_SHARED_SECRET` has been observed
"visible in env dumps" `[Rmem]`, and a `KeyProvider` port (Section 6) was **not found** in the
files read. `[U]`

## 3. Proposed model

**3.1 One user record, authoritative in Perpetua-Tools.** Single `operator` record: `user_id`,
`status` (`active`/`revoked`), `created_at`, `revision`. `revision` bumps on every enrolment and
revocation so a replica can be rejected as stale -- the discipline doc 61 already requires
("advance the revision on every revoke"). `[R61]` `[P]` One user, N credentials: credentials are
rows, not identities. `[P]`

**3.2 Credentials: one per device, plus one roaming key.** Each device enrols one platform
credential (device-bound authenticator in TPM / Secure Enclave); exactly one roaming FIDO2 key
is enrolled so a rebuilt host can still log in. Both are WebAuthn credentials bound to one RP ID
(Section 4) and the private key never leaves the authenticator -- the split the sentinel design
assumes: "The agent runtime never holds the human verification key." `[P]` `[R51]`

**3.3 The per-user data key.** One random 32-byte DEK per user, created at first enrolment, not
rotated by login. Kept only as N wraps, one per credential, each AEAD with AAD binding
`user_id`, `credential_id`, and `wrap_version`, so a wrap cannot move between users or
credentials and unwraps only against a fresh assertion. No unwrapped DEK is on disk or in any
config. `[P]`

**3.4 PRF wrapping, with a per-machine fallback.** Preferred: the WebAuthn PRF extension returns
a stable 32-byte secret per credential, and the KEK is derived with a salt bound to the
challenge, so the KEK is never stored. Fallback where PRF is unsupported: a per-machine key in
the OS keystore (Keychain item, DPAPI blob, Secret Service entry). It resists file copy and
backup extraction, not a same-user process (Section 9), so `kek_source = prf | os-keystore` is
recorded per wrap and weak wraps stay auditable. `[P]` PRF availability on the operator's real
browsers and authenticators is unverified. `[U]`

## 4. The relying-party-id problem

**4.1 The constraint.** A credential is bound to one RP ID, and an RP ID must be a domain
string: an IP literal is not a usable RP ID, and the browser origin's host must equal the RP ID
or be its subdomain. `[P]` The fleet dials raw IPs by design (layer 2 hostname == "the URL host =
the raw IP"), so today's addresses cannot carry a credential at all. `[Rsem]` `[P]`

**4.2 One stable shared name.** All hosts must serve one stable DNS name the browser can reach
on every host (hosts file, split-horizon DNS, or mDNS -- the resolution choice is an operator
decision). `[P]` The enrolment origin is fixed once: scheme + shared name + port. Port is not
part of the RP ID check, so `8443` / `8002` / `8001` can all serve one RP ID; only the host must
match. `[P]` Every leaf must then carry the shared name as a **DNS SAN** beside the IP SAN the
peer mesh requires; hostname binding already fails this way in practice ("certificate is not
valid for the previous Mac host"). `[P]` `[Rmem]`

**4.3 What that means for the pinned CA.** Still one CA, one pin, one custody host; the pinning
discipline does not change. `[P]` But CA authority grows: it can now mint a leaf asserting the
operator-facing origin name, so a CA key compromise escalates from "peer transport" to "an
origin the browser will accept for passkeys". `[P]` Required mitigations: a sign-time allowlist
of permitted DNS SANs, a shared name inside a namespace the fleet owns that cannot collide with
a public registrable domain, and the existing fail-closed pin check ("PEER_CA_FILE does not
match PEER_CA_SHA256; refusing to trust it"). Certificates stop carrying operator identity: a
valid leaf will mean "this transport reached an authorised host", nothing more. `[Rmem]` `[P]`

## 5. Enrolment and revocation flows

| Step | Action | Rule |
| --- | --- | --- |
| 1 | Operator opens the fixed origin and the existing control-plane bearer is accepted **once**, with the row recording `mode = grandfathered`. `[P]` | Bootstrap only, once per user |
| 2 | Perpetua-Tools mints a single-use challenge: TTL, `user_id`, device label, nonce, registry `revision`. `[P]` | Single use, short TTL |
| 3 | Browser calls `navigator.credentials.create` with `rpId` = shared name, user verification required, PRF requested. `[P]` | `rpId` is the one shared name (Section 4) |
| 4 | Perpetua-Tools verifies the attestation, refuses duplicate credential ids, stores public key, `aaguid`, transports, `prf_supported`. `[P]` | Registry `revision` bumps |
| 5 | The first credential generates the DEK; later ones need a second assertion from an existing credential to unwrap and re-wrap it. `[P]` | No usable credential means refusal, never a guess |
| 6 | Revoke one credential: set `revoked_at`, delete its wrap, bump `revision`. The DEK is untouched, so siblings keep working. Revoking the user disables every credential and the key provider returns nothing. `[P]` | Immediate, checked at assertion time -- unlike leaf revocation, which has no CRL/OCSP path today `[Rsem]` |
| 7 | Total credential loss: a sealed one-time recovery code over a memory-hard KDF, or accepted DEK loss (Section 12). Each step writes an audit row and one GossipBus `identity.enrolment` event. `[P]` | A missing receipt is `unknown`, never permission to retry |

## 6. Interaction with the session key store

- The store changes shape, not location: a `KeyProvider` port resolves the per-user key for a
  session. `[P]` No `KeyProvider` symbol exists in the files read. `[U]`
- Contract: `resolve(user_id) -> UserKey | None`, plus an explicit `mode` (`per-user` |
  `legacy-control-plane` | `absent`). `None` means **deny**, never "use a default"; new
  installs have no default key, so consumers refuse with an observable reason. `[P]`
- The control-plane key stays as the grandfathered development mode: a
  `ControlPlaneKeyProvider` answers only when the legacy token is present **and** an explicit
  flag is set; each use writes a warning row tagged `mode = legacy-control-plane` and is never
  auto-selected. Modes are never blended, so an audit can separate them. `[P]`
- Already documented: under the legacy mode all callers share one Level 0 quota bucket. `[R71]`

## 7. Human-presence proof for spend arming

- Today `preflight()` checks an on-disk attestation record and refuses with
  `attestation-required`; a static file cannot tell a human from an agent. `[Rspend]` `[P]`
- Proposed: Perpetua-Tools mints an arming challenge bound to the exact preview -- a canonical
  JSON digest over provider, seat, mode, model, projected amount, budget window and expiry --
  plus a nonce, a short TTL, and single-use state. `[P]`
- Only the browser relays the assertion. The PRF eval salt is derived from
  `challenge_id || preview_digest`, so one ceremony proves presence and releases the DEK wrap,
  and the PRF output is useless for any other preview. `[P]`
- Perpetua-Tools verifies signature, user-verification flag, RP ID, origin, TTL, single use
  and digest equality, then stores the arming record `preflight()` consumes. Absent, expired,
  consumed, or preview-changed challenges all refuse, and a consumed challenge is never
  licence to mint a replacement automatically. `[P]`
- Presence is the WebAuthn user-verification gesture, not a long press: hold-to-confirm is not
  identity. `[P]` This matches the framing already stated: "No irreversible action without a
  server-issued, time-limited approval that binds the reviewed preview to the launch", and
  "No agent may self-approve". `[R70]`

## 8. Consumer boundary rule

- Crypto verification belongs to Phylax, which owns signing, the public-key registry and
  revocation state and exposes a verify-only interface; the serving process "must not load a
  seed, P5 secret, or issuer-write capability". `[R71]`
- orama-system gets an injected verifier port only:
  `verify(assertion, expectation) -> Verified | Rejected | Unavailable`, deny by default and
  fail closed. Doc 62's consumer rule has the same shape: a consumer "MUST NOT maintain a
  permanent independent endpoint-security implementation", and "There is no silent
  direct-network fallback ... Failure to obtain a valid Telos result is fail-closed." `[R62]` `[P]`
- `Unavailable` is a refusal, never an assumption of success and never a trigger for a local
  re-implementation. One verifier of record per surface: Perpetua-Tools verifies its own
  portal, orama consumes the port for its own surfaces. No third implementation. `[P]` `[R62]`

## 9. Threat model: a same-user local agent

- Private keys are non-exportable, so an agent can only ask a browser to use them, and user
  verification needs the operator; PRF wraps derive the KEK per assertion and store nothing. `[P]`
- OS-keystore wraps are the soft spot: DPAPI is per-user (so a same-user process can decrypt)
  and a Keychain item may be granted to an agent running as the operator. Treat
  `kek_source = os-keystore` as transport-grade, not identity-grade. `[P]`
- An in-memory DEK is readable by a same-user debugger where the OS allows it; residual risk,
  documented, not solved. Agents can spam challenge minting: rate-limit per user and host. `[P]`
- A same-user agent can read the legacy tokens, so the grandfathered mode is no defence here;
  that is why it stays a development mode. Doc 61's honesty note applies: this raises the bar
  rather than closing the class. `[Rmem]` `[R61]` `[P]`
- Out of scope: kernel or hypervisor attackers, counterfeit authenticators, browser compromise,
  an unlocked unattended device, and DEK loss. `[P]`

## 10. Migration without breaking the bearer mesh

- Grandfathered, never forced: bearer stays registered and last in priority, exactly as doc 49
  specifies. `[R49]`
- M-D7-0 is today (machine identity only). M-D7-1 is opt-in: user record, credentials, and
  `KeyProvider`, while users with no credentials keep the bearer path and the legacy provider
  stays enabled wherever the old token exists -- zero change for existing installs. `[P]`
- M-D7-2 covers new surfaces only: the presence path is required for new installs and new
  sensitive actions, while existing installs keep the old path with a warning row. M-D7-3 is an
  operator decision per action, with no global cutover date and no forced re-enrolment. `[P]`
- Never, at any stage: rotate the shared token as a side effect, require the presence path on the
  peer mesh, or move the CA key off its custody host. `[R49]` `[Rsem]` `[P]`
- Rollback: deleting credentials never deletes the DEK; a user with zero credentials falls back to
  legacy only if the legacy key is present, otherwise refuses. `[P]`

## 11. Test plan

Each test file lands with the source file it pins; no library version is pinned here.

- Challenges: TTL expiry, single use, replay, wrong `preview_digest`, wrong `user_id`, stale
  `revision`, clock skew at the boundary.
- Assertions: unknown or revoked credential, revoked user, verification flag false, wrong RP ID,
  wrong origin, IP-literal origin, sign-count regression, malformed key.
- Wraps: AAD mismatch across `user_id` / `credential_id` / `wrap_version`, tampered ciphertext,
  substituted wrap from another user, and a PRF-less authenticator that must not silently take
  the PRF path.
- Cross-host and CA: the shared name accepted on two hosts, a different host name refused, a leaf
  without the DNS SAN refused, an off-roster SAN refused at sign time, pin mismatch still refused.
- `KeyProvider`: new install returns `None`, legacy mode needs token and flag, no implicit
  default, and every consumer refuses on `None`.
- Spend arming and migration: a preview edit or expiry invalidates, a second use refuses, success
  arms exactly one preflight, and the bearer suite passes unchanged with the flag off.
- Determinism: a fake in-process authenticator, no hardware, no network, no wall clock.

## 12. Open questions for the operator

1. Which stable shared name, and who owns its resolution on each host? `[P]`
2. Is it inside a registrable domain the fleet controls, or a `.local`-style name? `[P]`
3. Is one roaming key enough, or is a second held off-site? `[P]`
4. All authenticators lost: sealed recovery code, or accepted DEK loss and re-enrolment? `[P]`
5. Attestation policy: accept "none", or require vendor attestation for the roaming key? `[P]`
6. Where does the verifier run -- same host, separate account, separate process? Doc 71's Level 1
   gate requires an isolated signer and a seed-free server. `[R71]`
7. Which actions become presence-required first: spend arming only, or Class-3/4 from doc 70's
   portal table? `[R70]`
8. Is the browser the only relay, or is a headless-host fallback required? Doc 51 leaves "single
   sentinel per machine vs fleet-wide approval service" open. `[R51]`
9. Re-key the DEK on every revocation (forward secrecy) or only on recovery (convenience)? `[P]`
10. Do these rows land in the HMAC-chained audit log that doc 49 still lists as not implemented,
    and who signs off additions to the CA SAN allowlist? `[R49]` `[P]`
