/**
 * Authority Proof and Intent Confirmation Contract.
 *
 * CRITICAL ARCHITECTURAL INVARIANTS:
 * 1. Browser ONLY relays proof; never stores proof in localStorage, sessionStorage, or document.cookie.
 * 2. Zero browser-side cryptographic verification (verification belongs strictly to the PT server).
 * 3. Explicitly no "hold-to-confirm" as identity proof. Hold gestures capture UI intent only.
 * 4. No assumption of Mac (Touch ID) and Windows (Windows Hello) authenticator parity.
 *
 * Immutability: all data structures are strictly readonly.
 */

/** Permitted authority proof types accepted by the PT authority server. */
export type ProofType =
  | 'webauthn_touch_id'
  | 'webauthn_security_key'
  | 'operator_attestation';

export const VALID_PROOF_TYPES: readonly ProofType[] = Object.freeze([
  'webauthn_touch_id',
  'webauthn_security_key',
  'operator_attestation',
]);

/**
 * Opaque authority proof relay structure.
 * Relayed verbatim from authenticators/operators to the PT server.
 * The browser never decrypts, unpacks, or cryptographically validates this payload.
 */
export interface AuthorityProof {
  readonly rawProof: string;
  readonly proofType: ProofType;
  readonly issuedAt: string;
  readonly expiresAt: string;
  readonly deviceId: string;
}

/** Prohibited pseudo-proof origins that must NEVER be treated as authority proof. */
export type ProhibitedProofSource =
  | 'hold_to_confirm'
  | 'dialog_click'
  | 'client_checkbox';

export const PROHIBITED_SOURCES: readonly ProhibitedProofSource[] = Object.freeze([
  'hold_to_confirm',
  'dialog_click',
  'client_checkbox',
]);

/** Forbidden storage mechanisms for authority proofs. Proofs are memory-only relays. */
export const FORBIDDEN_STORAGE_TARGETS = Object.freeze([
  'localStorage',
  'sessionStorage',
  'cookie',
  'document.cookie',
  'indexedDB',
] as const);

export type ForbiddenStorageTarget = (typeof FORBIDDEN_STORAGE_TARGETS)[number];

/** Supported host platforms for authenticator resolution. */
export type HostPlatform = 'mac' | 'windows' | 'linux' | 'unknown';

/**
 * Host authenticator capabilities reflecting disparity between platforms.
 * Explicitly rejects false equivalence between macOS Touch ID and Windows Hello.
 */
export interface HostAuthenticatorCapabilities {
  readonly platform: HostPlatform;
  readonly supportsTouchId: boolean;
  readonly supportsWindowsHello: boolean;
  readonly supportsSecurityKey: boolean;
  readonly supportsOperatorAttestation: boolean;
  readonly permittedProofTypes: readonly ProofType[];
  readonly disparityNotice: string;
}

export const HOST_AUTHENTICATOR_CAPABILITIES: Readonly<Record<HostPlatform, HostAuthenticatorCapabilities>> = Object.freeze({
  mac: Object.freeze({
    platform: 'mac',
    supportsTouchId: true,
    supportsWindowsHello: false,
    supportsSecurityKey: true,
    supportsOperatorAttestation: true,
    permittedProofTypes: Object.freeze<ProofType[]>([
      'webauthn_touch_id',
      'webauthn_security_key',
      'operator_attestation',
    ]),
    disparityNotice: 'macOS Secure Enclave provides Touch ID platform authenticator via WebAuthn uv=preferred.',
  }),
  windows: Object.freeze({
    platform: 'windows',
    supportsTouchId: false,
    supportsWindowsHello: true,
    supportsSecurityKey: true,
    supportsOperatorAttestation: true,
    // Note: Windows Hello uses distinct authenticator transport and assertion format.
    // It does NOT have parity with webauthn_touch_id.
    permittedProofTypes: Object.freeze<ProofType[]>([
      'webauthn_security_key',
      'operator_attestation',
    ]),
    disparityNotice: 'Windows Hello does not have attestation parity with macOS Touch ID. Use security key or operator attestation.',
  }),
  linux: Object.freeze({
    platform: 'linux',
    supportsTouchId: false,
    supportsWindowsHello: false,
    supportsSecurityKey: true,
    supportsOperatorAttestation: true,
    permittedProofTypes: Object.freeze<ProofType[]>([
      'webauthn_security_key',
      'operator_attestation',
    ]),
    disparityNotice: 'Linux lacks unified platform biometric authenticator; requires roaming security key or operator attestation.',
  }),
  unknown: Object.freeze({
    platform: 'unknown',
    supportsTouchId: false,
    supportsWindowsHello: false,
    supportsSecurityKey: true,
    supportsOperatorAttestation: true,
    permittedProofTypes: Object.freeze<ProofType[]>([
      'webauthn_security_key',
      'operator_attestation',
    ]),
    disparityNotice: 'Unknown host environment; platform authenticator parity assumed unavailable.',
  }),
});

/**
 * Returns host authenticator capability descriptor.
 */
export function getHostAuthenticatorCapabilities(platform: HostPlatform): HostAuthenticatorCapabilities {
  return HOST_AUTHENTICATOR_CAPABILITIES[platform] ?? HOST_AUTHENTICATOR_CAPABILITIES.unknown;
}

/**
 * Checks if a specific proof type is permitted on a given host platform.
 */
export function isProofTypePermittedOnHost(proofType: ProofType, platform: HostPlatform): boolean {
  const caps = getHostAuthenticatorCapabilities(platform);
  return caps.permittedProofTypes.includes(proofType);
}

/** Sensitive operation identifiers requiring confirmation or authority proof. */
export type SensitiveOperation =
  | 'service_stop'
  | 'service_restart'
  | 'peer_rediscover'
  | 'spend_cap_arm';

export interface IntentConfirmationCopy {
  readonly title: string;
  readonly description: string;
  readonly confirmLabel: string;
  readonly cancelLabel: string;
  readonly requiresAuthorityProof: boolean;
  readonly intentOnlyWarning?: string;
}

/**
 * Intent confirmation copy dictionary for sensitive operations.
 * Enforces clear separation between intent confirmation and server authority.
 */
export const INTENT_CONFIRMATION_COPY: Readonly<Record<SensitiveOperation, IntentConfirmationCopy>> = Object.freeze({
  service_stop: Object.freeze({
    title: 'Stop Service',
    description: 'Halts the active portal daemon and terminates local background workers. In-flight operations will be interrupted. The service will stop responding to local RPC requests until restarted manually.',
    confirmLabel: 'Stop Service',
    cancelLabel: 'Keep Running',
    requiresAuthorityProof: false,
  }),
  service_restart: Object.freeze({
    title: 'Restart Service',
    description: 'Gracefully cycles the portal service process and reloads runtime configurations. In-flight tasks will complete before process recycling. Connected clients will experience a momentary reconnect.',
    confirmLabel: 'Restart Service',
    cancelLabel: 'Cancel',
    requiresAuthorityProof: false,
  }),
  peer_rediscover: Object.freeze({
    title: 'Rediscover Peer Network',
    description: 'Triggers a full network discovery broadcast to detect active LAN peers and synchronize gossip bus routing tables. Existing peer sessions will renegotiate liveness.',
    confirmLabel: 'Scan Peers',
    cancelLabel: 'Cancel',
    requiresAuthorityProof: false,
  }),
  spend_cap_arm: Object.freeze({
    title: 'Arm Spend Cap Override',
    description: 'Requests elevation of provider spending caps for external LLM API and compute allocations.',
    confirmLabel: 'Acknowledge Intent',
    cancelLabel: 'Cancel',
    requiresAuthorityProof: true,
    intentOnlyWarning: 'Intent confirmation only: clicking confirm here records operator intent in the client UI. It DOES NOT authorize spend. Spend authorization requires server-verified authority proof (WebAuthn or Operator Attestation).',
  }),
});

/**
 * Retrieves immutable copy dictionary entry for sensitive operation confirmation.
 */
export function getIntentConfirmationCopy(operation: SensitiveOperation): IntentConfirmationCopy {
  const copy = INTENT_CONFIRMATION_COPY[operation];
  if (!copy) {
    throw new Error(`Unknown sensitive operation: ${String(operation)}`);
  }
  return copy;
}

/**
 * Validates ISO 8601 timestamp string format.
 */
export function isValidIsoTimestamp(value: unknown): value is string {
  if (typeof value !== 'string' || value.trim().length === 0) {
    return false;
  }
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return false;
  }
  return !Number.isNaN(new Date(value).getTime());
}

/**
 * Type guard for AuthorityProof.
 * Validates structural integrity without performing cryptographic verification.
 */
export function isValidAuthorityProof(candidate: unknown): candidate is AuthorityProof {
  if (typeof candidate !== 'object' || candidate === null) {
    return false;
  }
  const proof = candidate as Record<string, unknown>;

  if (typeof proof.rawProof !== 'string' || proof.rawProof.trim().length === 0) {
    return false;
  }
  if (!VALID_PROOF_TYPES.includes(proof.proofType as ProofType)) {
    return false;
  }
  if (!isValidIsoTimestamp(proof.issuedAt)) {
    return false;
  }
  if (!isValidIsoTimestamp(proof.expiresAt)) {
    return false;
  }
  if (Date.parse(proof.expiresAt) <= Date.parse(proof.issuedAt)) {
    return false;
  }
  if (typeof proof.deviceId !== 'string' || proof.deviceId.trim().length === 0) {
    return false;
  }
  return true;
}

/**
 * Checks whether an authority proof has expired relative to a reference time.
 */
export function isAuthorityProofExpired(proof: AuthorityProof, nowIso?: string): boolean {
  const referenceTime = nowIso ? Date.parse(nowIso) : Date.now();
  const expiresAtTime = Date.parse(proof.expiresAt);
  return expiresAtTime <= referenceTime;
}

/** Relay validation outcome */
export type ProofRelayValidationResult =
  | { readonly ok: true; readonly proof: AuthorityProof }
  | { readonly ok: false; readonly error: string };

/**
 * Validates an authority proof candidate for relay readiness.
 * Note: Performs structural validation only; zero cryptographic verification is performed in the browser.
 */
export function validateAuthorityProofRelay(candidate: unknown, nowIso?: string): ProofRelayValidationResult {
  if (!isValidAuthorityProof(candidate)) {
    return {
      ok: false,
      error: 'Invalid authority proof structure: missing required fields or invalid timestamps.',
    };
  }
  if (isAuthorityProofExpired(candidate, nowIso)) {
    return {
      ok: false,
      error: `Authority proof expired at ${candidate.expiresAt}.`,
    };
  }
  return {
    ok: true,
    proof: candidate,
  };
}

/**
 * Asserts that candidate is a valid AuthorityProof, throwing TypeError otherwise.
 */
export function assertValidAuthorityProof(candidate: unknown, nowIso?: string): asserts candidate is AuthorityProof {
  const result = validateAuthorityProofRelay(candidate, nowIso);
  if (!result.ok) {
    throw new TypeError(result.error);
  }
}

/**
 * Safety invariant: explicitly forbids 'hold_to_confirm' or UI gesture from being used as authority proof.
 */
export function assertNoHoldToConfirm(candidate: { readonly proofType?: unknown; readonly source?: unknown }): void {
  if (candidate.proofType === 'hold_to_confirm' || candidate.source === 'hold_to_confirm') {
    throw new Error('Hold-to-confirm is an intent gesture, never valid authority proof.');
  }
}

/**
 * Safety invariant: explicitly forbids storing authority proofs in persistent browser storage.
 */
export function assertNoPersistenceAttempt(targetName: string): void {
  const normalized = targetName.toLowerCase();
  for (const forbidden of FORBIDDEN_STORAGE_TARGETS) {
    if (normalized.includes(forbidden.toLowerCase())) {
      throw new Error(
        `Browser relay safety violation: authority proof persistence to ${targetName} is strictly forbidden.`
      );
    }
  }
}

/**
 * Simulates storage write attempt guard. Prevents authority proofs from being persisted.
 */
export function guardProofStorageWrite(target: string, value: unknown): void {
  assertNoPersistenceAttempt(target);
  if (isValidAuthorityProof(value)) {
    throw new Error(`Cannot write AuthorityProof to storage target: ${target}`);
  }
}
