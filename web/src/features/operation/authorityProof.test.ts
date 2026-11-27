import { describe, expect, it } from 'vitest';
import {
  type AuthorityProof,
  FORBIDDEN_STORAGE_TARGETS,
  HOST_AUTHENTICATOR_CAPABILITIES,
  INTENT_CONFIRMATION_COPY,
  VALID_PROOF_TYPES,
  assertNoHoldToConfirm,
  assertNoPersistenceAttempt,
  assertValidAuthorityProof,
  getHostAuthenticatorCapabilities,
  getIntentConfirmationCopy,
  guardProofStorageWrite,
  isAuthorityProofExpired,
  isProofTypePermittedOnHost,
  isValidAuthorityProof,
  isValidIsoTimestamp,
  validateAuthorityProofRelay,
} from './authorityProof';

describe('isValidIsoTimestamp', () => {
  it('accepts valid ISO 8601 strings', () => {
    expect(isValidIsoTimestamp('2026-11-27T00:00:00.000Z')).toBe(true);
    expect(isValidIsoTimestamp('2026-11-27T12:34:56Z')).toBe(true);
  });

  it('rejects invalid timestamp strings or non-string inputs', () => {
    expect(isValidIsoTimestamp('')).toBe(false);
    expect(isValidIsoTimestamp('not-a-date')).toBe(false);
    expect(isValidIsoTimestamp(null)).toBe(false);
    expect(isValidIsoTimestamp(12345678)).toBe(false);
  });
});

describe('AuthorityProof Validation and Relay', () => {
  const validProof: AuthorityProof = {
    rawProof: 'opaque_base64_attestation_bytes_signed_by_authenticator',
    proofType: 'webauthn_touch_id',
    issuedAt: '2026-11-27T10:00:00.000Z',
    expiresAt: '2026-11-27T10:05:00.000Z',
    deviceId: 'dev_macbook_pro_m3_secure_enclave',
  };

  it('accepts fully compliant authority proof structures', () => {
    expect(isValidAuthorityProof(validProof)).toBe(true);
  });

  it('accepts all allowed proof types', () => {
    for (const proofType of VALID_PROOF_TYPES) {
      const proof: AuthorityProof = {
        ...validProof,
        proofType,
      };
      expect(isValidAuthorityProof(proof)).toBe(true);
    }
  });

  it('rejects proof with missing or empty rawProof', () => {
    expect(isValidAuthorityProof({ ...validProof, rawProof: '' })).toBe(false);
    expect(isValidAuthorityProof({ ...validProof, rawProof: '   ' })).toBe(false);
    expect(isValidAuthorityProof({ ...validProof, rawProof: undefined })).toBe(false);
  });

  it('rejects proof with unpermitted proofType', () => {
    expect(isValidAuthorityProof({ ...validProof, proofType: 'password' })).toBe(false);
    expect(isValidAuthorityProof({ ...validProof, proofType: 'hold_to_confirm' })).toBe(false);
  });

  it('rejects proof with invalid timestamps or expiresAt earlier than issuedAt', () => {
    expect(isValidAuthorityProof({ ...validProof, issuedAt: 'invalid' })).toBe(false);
    expect(isValidAuthorityProof({ ...validProof, expiresAt: 'invalid' })).toBe(false);
    expect(
      isValidAuthorityProof({
        ...validProof,
        issuedAt: '2026-11-27T10:05:00.000Z',
        expiresAt: '2026-11-27T10:00:00.000Z',
      })
    ).toBe(false);
    expect(
      isValidAuthorityProof({
        ...validProof,
        issuedAt: '2026-11-27T10:00:00.000Z',
        expiresAt: '2026-11-27T10:00:00.000Z',
      })
    ).toBe(false);
  });

  it('rejects proof with missing or empty deviceId', () => {
    expect(isValidAuthorityProof({ ...validProof, deviceId: '' })).toBe(false);
    expect(isValidAuthorityProof({ ...validProof, deviceId: '  ' })).toBe(false);
    expect(isValidAuthorityProof({ ...validProof, deviceId: null })).toBe(false);
  });

  it('rejects non-object or null candidates', () => {
    expect(isValidAuthorityProof(null)).toBe(false);
    expect(isValidAuthorityProof(undefined)).toBe(false);
    expect(isValidAuthorityProof('string')).toBe(false);
    expect(isValidAuthorityProof(12345)).toBe(false);
  });

  it('detects expired proof correctly against reference timestamps', () => {
    const expiredRef = '2026-11-27T10:06:00.000Z';
    const activeRef = '2026-11-27T10:02:00.000Z';
    const exactExpireRef = '2026-11-27T10:05:00.000Z';

    expect(isAuthorityProofExpired(validProof, expiredRef)).toBe(true);
    expect(isAuthorityProofExpired(validProof, exactExpireRef)).toBe(true);
    expect(isAuthorityProofExpired(validProof, activeRef)).toBe(false);
  });

  it('validates proof relay and returns typed result', () => {
    const activeRef = '2026-11-27T10:01:00.000Z';
    const result = validateAuthorityProofRelay(validProof, activeRef);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.proof).toEqual(validProof);
    }

    const expiredResult = validateAuthorityProofRelay(validProof, '2026-11-27T10:10:00.000Z');
    expect(expiredResult.ok).toBe(false);
    if (!expiredResult.ok) {
      expect(expiredResult.error).toContain('Authority proof expired');
    }

    const invalidResult = validateAuthorityProofRelay({ bad: true });
    expect(invalidResult.ok).toBe(false);
    if (!invalidResult.ok) {
      expect(invalidResult.error).toContain('Invalid authority proof structure');
    }
  });

  it('assertValidAuthorityProof asserts validity or throws TypeError', () => {
    const activeRef = '2026-11-27T10:01:00.000Z';
    expect(() => assertValidAuthorityProof(validProof, activeRef)).not.toThrow();
    expect(() => assertValidAuthorityProof({ bad: true })).toThrow(TypeError);
  });
});

describe('Browser Relay Safety Invariants', () => {
  it('strictly forbids hold-to-confirm as authority proof', () => {
    expect(() => assertNoHoldToConfirm({ proofType: 'hold_to_confirm' })).toThrow(
      /Hold-to-confirm is an intent gesture, never valid authority proof/
    );
    expect(() => assertNoHoldToConfirm({ source: 'hold_to_confirm' })).toThrow(
      /Hold-to-confirm is an intent gesture, never valid authority proof/
    );
    expect(() => assertNoHoldToConfirm({ proofType: 'webauthn_touch_id' })).not.toThrow();
  });

  it('forbids persistence to localStorage, sessionStorage, and cookies', () => {
    for (const target of FORBIDDEN_STORAGE_TARGETS) {
      expect(() => assertNoPersistenceAttempt(target)).toThrow(
        /Browser relay safety violation: authority proof persistence/
      );
    }
    expect(() => assertNoPersistenceAttempt('window.localStorage')).toThrow();
    expect(() => assertNoPersistenceAttempt('document.cookie')).toThrow();

    // Memory-only relay targets are allowed
    expect(() => assertNoPersistenceAttempt('in_memory_relay_queue')).not.toThrow();
    expect(() => assertNoPersistenceAttempt('http_authorization_header')).not.toThrow();
  });

  it('guardProofStorageWrite blocks writing proofs to storage targets', () => {
    const sampleProof: AuthorityProof = {
      rawProof: 'opaque_bytes',
      proofType: 'operator_attestation',
      issuedAt: '2026-11-27T10:00:00.000Z',
      expiresAt: '2026-11-27T10:10:00.000Z',
      deviceId: 'op_terminal_01',
    };

    expect(() => guardProofStorageWrite('localStorage', sampleProof)).toThrow();
    expect(() => guardProofStorageWrite('sessionStorage', sampleProof)).toThrow();
    expect(() => guardProofStorageWrite('document.cookie', sampleProof)).toThrow();
    expect(() => guardProofStorageWrite('memory_bus', sampleProof)).toThrow(
      /Cannot write AuthorityProof to storage target: memory_bus/
    );
  });
});

describe('Intent Confirmation Copy Dictionary', () => {
  it('defines distinct, accurate confirmation copy for all sensitive operations', () => {
    const stopCopy = getIntentConfirmationCopy('service_stop');
    expect(stopCopy.title).toBe('Stop Service');
    expect(stopCopy.description).toContain('Halts the active portal daemon');
    expect(stopCopy.requiresAuthorityProof).toBe(false);

    const restartCopy = getIntentConfirmationCopy('service_restart');
    expect(restartCopy.title).toBe('Restart Service');
    expect(restartCopy.description).toContain('Gracefully cycles the portal service');
    expect(restartCopy.requiresAuthorityProof).toBe(false);

    const rediscoverCopy = getIntentConfirmationCopy('peer_rediscover');
    expect(rediscoverCopy.title).toBe('Rediscover Peer Network');
    expect(rediscoverCopy.description).toContain('Triggers a full network discovery broadcast');
    expect(rediscoverCopy.requiresAuthorityProof).toBe(false);

    const spendCopy = getIntentConfirmationCopy('spend_cap_arm');
    expect(spendCopy.title).toBe('Arm Spend Cap Override');
    expect(spendCopy.requiresAuthorityProof).toBe(true);
    expect(spendCopy.intentOnlyWarning).toBeDefined();
    expect(spendCopy.intentOnlyWarning).toContain('Intent confirmation only');
    expect(spendCopy.intentOnlyWarning).toMatch(/does not authorize spend/i);
  });

  it('guarantees immutability of the dictionary', () => {
    expect(Object.isFrozen(INTENT_CONFIRMATION_COPY)).toBe(true);
    expect(Object.isFrozen(INTENT_CONFIRMATION_COPY.service_stop)).toBe(true);
    expect(Object.isFrozen(INTENT_CONFIRMATION_COPY.spend_cap_arm)).toBe(true);
  });

  it('throws on unknown operations', () => {
    // @ts-expect-error Testing invalid runtime input
    expect(() => getIntentConfirmationCopy('unknown_operation')).toThrow(
      /Unknown sensitive operation/
    );
  });
});

describe('Host Authenticator Disparity Handling', () => {
  it('does not assume parity between macOS Touch ID and Windows Hello', () => {
    const macCaps = getHostAuthenticatorCapabilities('mac');
    const winCaps = getHostAuthenticatorCapabilities('windows');
    const linuxCaps = getHostAuthenticatorCapabilities('linux');

    expect(macCaps.supportsTouchId).toBe(true);
    expect(macCaps.supportsWindowsHello).toBe(false);
    expect(macCaps.permittedProofTypes).toContain('webauthn_touch_id');

    expect(winCaps.supportsTouchId).toBe(false);
    expect(winCaps.supportsWindowsHello).toBe(true);
    // Explicit disparity check: webauthn_touch_id is NOT permitted on Windows
    expect(winCaps.permittedProofTypes).not.toContain('webauthn_touch_id');
    expect(winCaps.disparityNotice).toContain('Windows Hello does not have attestation parity');

    expect(linuxCaps.supportsTouchId).toBe(false);
    expect(linuxCaps.supportsWindowsHello).toBe(false);
  });

  it('correctly reports supported proof types per host platform', () => {
    expect(isProofTypePermittedOnHost('webauthn_touch_id', 'mac')).toBe(true);
    expect(isProofTypePermittedOnHost('webauthn_touch_id', 'windows')).toBe(false);
    expect(isProofTypePermittedOnHost('webauthn_touch_id', 'linux')).toBe(false);

    expect(isProofTypePermittedOnHost('webauthn_security_key', 'mac')).toBe(true);
    expect(isProofTypePermittedOnHost('webauthn_security_key', 'windows')).toBe(true);
    expect(isProofTypePermittedOnHost('webauthn_security_key', 'linux')).toBe(true);

    expect(isProofTypePermittedOnHost('operator_attestation', 'windows')).toBe(true);
  });

  it('falls back to unknown capabilities safely for unrecognized platforms', () => {
    const unknownCaps = getHostAuthenticatorCapabilities('unknown');
    expect(unknownCaps.supportsTouchId).toBe(false);
    expect(unknownCaps.supportsWindowsHello).toBe(false);
    expect(unknownCaps.disparityNotice).toContain('Unknown host environment');
  });
});
