import { describe, expect, it } from "vitest";
import {
  canRequestAuthority,
  canRetry,
  INITIAL_OPERATION_STATE,
  isReceiptVerified,
  isTerminalState,
  isWaitingForAuthority,
  operationReducer,
  type AuthorityProof,
  type DiagnosticFailureInfo,
  type OperationEvent,
  type OperationParams,
  type OperationReceipt,
  type OperationState,
  type OperationStatus,
  type PreviewData,
  type RefusalInfo,
} from "./operationState";

const mockParams: OperationParams = {
  operationId: "op-100",
  action: "DEPLOY_ARTIFACT",
  payload: { target: "prod-cluster-01", replicas: 3 },
  paramHash: "hash-initial-123",
};

const mockUpdatedParams: OperationParams = {
  operationId: "op-100",
  action: "DEPLOY_ARTIFACT",
  payload: { target: "prod-cluster-01", replicas: 5 },
  paramHash: "hash-modified-456",
};

const mockPreview: PreviewData = {
  previewId: "prev-999",
  paramHash: "hash-initial-123",
  estimatedCost: 14.5,
  summary: "Deploying 3 pods to cluster",
  expiresAt: 5000,
};

const mockAuthority: AuthorityProof = {
  proofId: "proof-42",
  authorizedBy: "operator@example.com",
  timestamp: 1000,
  signature: "ed25519-sig-xyz",
};

const mockReceipt: OperationReceipt = {
  receiptId: "receipt-777",
  timestamp: 2000,
  signature: "receipt-sig-abc",
  details: { deploymentId: "dep-001" },
};

const mockRefusal: RefusalInfo = {
  code: "POLICY_VIOLATION",
  reason: "Resource quota exceeded for environment prod-cluster-01",
  policy: "strict-infra-bounds",
};

const mockFailure: DiagnosticFailureInfo = {
  code: "CONTAINER_CRASH",
  reason: "OOMKilled exit code 137",
  diagnostic: "Process memory limit of 512MB exceeded during startup hook",
  stack: "RuntimeError at pod_boot.go:142",
};

describe("operationReducer - Complete Table-Driven Transitions", () => {
  interface TransitionTestCase {
    readonly name: string;
    readonly initialState: OperationState;
    readonly event: OperationEvent;
    readonly expectedStatus: OperationStatus;
    readonly assertion?: (nextState: OperationState) => void;
  }

  const testCases: TransitionTestCase[] = [
    // 1. IDLE -> PREVIEWING
    {
      name: "IDLE -> PREVIEWING on REQUEST_PREVIEW",
      initialState: INITIAL_OPERATION_STATE,
      event: {
        type: "REQUEST_PREVIEW",
        payload: { operationId: "op-100", params: mockParams },
      },
      expectedStatus: "PREVIEWING",
      assertion: (state) => {
        if (state.status === "PREVIEWING") {
          expect(state.operationId).toBe("op-100");
          expect(state.params).toEqual(mockParams);
          expect(state.preview).toBeUndefined();
        }
      },
    },

    // 2. PREVIEWING -> PREVIEWING (with preview loaded)
    {
      name: "PREVIEWING -> PREVIEWING on PREVIEW_READY",
      initialState: {
        status: "PREVIEWING",
        operationId: "op-100",
        params: mockParams,
      },
      event: {
        type: "PREVIEW_READY",
        payload: { preview: mockPreview },
      },
      expectedStatus: "PREVIEWING",
      assertion: (state) => {
        if (state.status === "PREVIEWING") {
          expect(state.preview).toEqual(mockPreview);
        }
      },
    },

    // 3. PREVIEWING -> PREVIEW_CHANGED on PARAMS_CHANGED
    {
      name: "PREVIEWING -> PREVIEW_CHANGED on PARAMS_CHANGED",
      initialState: {
        status: "PREVIEWING",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
      },
      event: {
        type: "PARAMS_CHANGED",
        payload: { updatedParams: mockUpdatedParams, reason: "Replicas modified" },
      },
      expectedStatus: "PREVIEW_CHANGED",
      assertion: (state) => {
        if (state.status === "PREVIEW_CHANGED") {
          expect(state.originalParams).toEqual(mockParams);
          expect(state.updatedParams).toEqual(mockUpdatedParams);
          expect(state.reason).toBe("Replicas modified");
        }
      },
    },

    // 4. PREVIEWING -> PREVIEW_EXPIRED on PREVIEW_EXPIRED event
    {
      name: "PREVIEWING -> PREVIEW_EXPIRED on PREVIEW_EXPIRED event",
      initialState: {
        status: "PREVIEWING",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
      },
      event: {
        type: "PREVIEW_EXPIRED",
        payload: { expiredAt: 5500 },
      },
      expectedStatus: "PREVIEW_EXPIRED",
      assertion: (state) => {
        if (state.status === "PREVIEW_EXPIRED") {
          expect(state.expiredAt).toBe(5500);
          expect(state.preview).toEqual(mockPreview);
        }
      },
    },

    // 5. PREVIEWING -> WAITING_FOR_AUTHORITY on REQUEST_AUTHORITY
    {
      name: "PREVIEWING -> WAITING_FOR_AUTHORITY on REQUEST_AUTHORITY (valid preview & timestamp)",
      initialState: {
        status: "PREVIEWING",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
      },
      event: {
        type: "REQUEST_AUTHORITY",
        payload: { requestedAt: 1200, currentTimestamp: 1200 },
      },
      expectedStatus: "WAITING_FOR_AUTHORITY",
      assertion: (state) => {
        if (state.status === "WAITING_FOR_AUTHORITY") {
          expect(state.requestedAt).toBe(1200);
          expect(state.preview).toEqual(mockPreview);
        }
      },
    },

    // 6. WAITING_FOR_AUTHORITY -> QUEUED on AUTHORITY_GRANTED
    {
      name: "WAITING_FOR_AUTHORITY -> QUEUED on AUTHORITY_GRANTED",
      initialState: {
        status: "WAITING_FOR_AUTHORITY",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
        requestedAt: 1200,
      },
      event: {
        type: "AUTHORITY_GRANTED",
        payload: { authority: mockAuthority, queuedAt: 1300, currentTimestamp: 1300 },
      },
      expectedStatus: "QUEUED",
      assertion: (state) => {
        if (state.status === "QUEUED") {
          expect(state.authority).toEqual(mockAuthority);
          expect(state.queuedAt).toBe(1300);
        }
      },
    },

    // 7. WAITING_FOR_AUTHORITY -> REFUSED on AUTHORITY_REFUSED
    {
      name: "WAITING_FOR_AUTHORITY -> REFUSED on AUTHORITY_REFUSED (policy/permission denial)",
      initialState: {
        status: "WAITING_FOR_AUTHORITY",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
        requestedAt: 1200,
      },
      event: {
        type: "AUTHORITY_REFUSED",
        payload: { refusal: mockRefusal, refusedAt: 1250 },
      },
      expectedStatus: "REFUSED",
      assertion: (state) => {
        if (state.status === "REFUSED") {
          expect(state.refusal).toEqual(mockRefusal);
          expect(state.refusal.policy).toBe("strict-infra-bounds");
          expect(state.refusedAt).toBe(1250);
        }
      },
    },

    // 8. WAITING_FOR_AUTHORITY -> PREVIEW_CHANGED on PARAMS_CHANGED
    {
      name: "WAITING_FOR_AUTHORITY -> PREVIEW_CHANGED on PARAMS_CHANGED (invalidates pending authority)",
      initialState: {
        status: "WAITING_FOR_AUTHORITY",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
        requestedAt: 1200,
      },
      event: {
        type: "PARAMS_CHANGED",
        payload: { updatedParams: mockUpdatedParams, reason: "Param mutated while waiting" },
      },
      expectedStatus: "PREVIEW_CHANGED",
      assertion: (state) => {
        if (state.status === "PREVIEW_CHANGED") {
          expect(state.updatedParams).toEqual(mockUpdatedParams);
          expect(state.reason).toBe("Param mutated while waiting");
        }
      },
    },

    // 9. WAITING_FOR_AUTHORITY -> PREVIEW_EXPIRED on timeout during authority grant
    {
      name: "WAITING_FOR_AUTHORITY -> PREVIEW_EXPIRED when AUTHORITY_GRANTED occurs after preview expires",
      initialState: {
        status: "WAITING_FOR_AUTHORITY",
        operationId: "op-100",
        params: mockParams,
        preview: { ...mockPreview, expiresAt: 2000 },
        requestedAt: 1200,
      },
      event: {
        type: "AUTHORITY_GRANTED",
        payload: { authority: mockAuthority, currentTimestamp: 2500 },
      },
      expectedStatus: "PREVIEW_EXPIRED",
      assertion: (state) => {
        if (state.status === "PREVIEW_EXPIRED") {
          expect(state.expiredAt).toBe(2500);
        }
      },
    },

    // 10. QUEUED -> ACCEPTED on ACCEPT_OPERATION
    {
      name: "QUEUED -> ACCEPTED on ACCEPT_OPERATION",
      initialState: {
        status: "QUEUED",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
        authority: mockAuthority,
        queuedAt: 1300,
      },
      event: {
        type: "ACCEPT_OPERATION",
        payload: { acceptedAt: 1400, executionId: "exec-001" },
      },
      expectedStatus: "ACCEPTED",
      assertion: (state) => {
        if (state.status === "ACCEPTED") {
          expect(state.acceptedAt).toBe(1400);
          expect(state.executionId).toBe("exec-001");
        }
      },
    },

    // 11. QUEUED -> REFUSED on REFUSE_OPERATION
    {
      name: "QUEUED -> REFUSED on REFUSE_OPERATION (distinct policy refusal at gateway)",
      initialState: {
        status: "QUEUED",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
        authority: mockAuthority,
        queuedAt: 1300,
      },
      event: {
        type: "REFUSE_OPERATION",
        payload: { refusal: mockRefusal, refusedAt: 1350 },
      },
      expectedStatus: "REFUSED",
      assertion: (state) => {
        if (state.status === "REFUSED") {
          expect(state.refusal.code).toBe("POLICY_VIOLATION");
        }
      },
    },

    // 12. QUEUED -> FAILED on EXECUTION_FAILED
    {
      name: "QUEUED -> FAILED on EXECUTION_FAILED",
      initialState: {
        status: "QUEUED",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
        authority: mockAuthority,
        queuedAt: 1300,
      },
      event: {
        type: "EXECUTION_FAILED",
        payload: { failure: mockFailure, failedAt: 1380 },
      },
      expectedStatus: "FAILED",
      assertion: (state) => {
        if (state.status === "FAILED") {
          expect(state.failure.code).toBe("CONTAINER_CRASH");
          expect(state.failure.diagnostic).toContain("512MB exceeded");
        }
      },
    },

    // 13. QUEUED -> UNKNOWN_COMPLETION on EXECUTION_DISCONNECTED
    {
      name: "QUEUED -> UNKNOWN_COMPLETION on EXECUTION_DISCONNECTED",
      initialState: {
        status: "QUEUED",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
        authority: mockAuthority,
        queuedAt: 1300,
      },
      event: {
        type: "EXECUTION_DISCONNECTED",
        payload: {
          reason: "Gateway TCP connection reset by peer during dispatch",
          disconnectedAt: 1390,
          details: "Socket closed before handshake ack",
        },
      },
      expectedStatus: "UNKNOWN_COMPLETION",
      assertion: (state) => {
        if (state.status === "UNKNOWN_COMPLETION") {
          expect(state.unknownCompletion.lastKnownStage).toBe("QUEUED");
          expect(state.unknownCompletion.reason).toContain("TCP connection reset");
        }
      },
    },

    // 14. ACCEPTED -> EXECUTED on EXECUTION_SUCCEEDED (with receipt)
    {
      name: "ACCEPTED -> EXECUTED on EXECUTION_SUCCEEDED with attached receipt",
      initialState: {
        status: "ACCEPTED",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
        authority: mockAuthority,
        acceptedAt: 1400,
        executionId: "exec-001",
      },
      event: {
        type: "EXECUTION_SUCCEEDED",
        payload: { receipt: mockReceipt, executedAt: 2000 },
      },
      expectedStatus: "EXECUTED",
      assertion: (state) => {
        if (state.status === "EXECUTED") {
          expect(state.receipt).toEqual(mockReceipt);
          expect(state.executedAt).toBe(2000);
        }
      },
    },

    // 15. ACCEPTED -> EXECUTED_RECEIPT_MISSING on EXECUTION_CONFIRMED_RECEIPT_MISSING
    {
      name: "ACCEPTED -> EXECUTED_RECEIPT_MISSING when backend confirmed without receipt attached",
      initialState: {
        status: "ACCEPTED",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
        authority: mockAuthority,
        acceptedAt: 1400,
        executionId: "exec-001",
      },
      event: {
        type: "EXECUTION_CONFIRMED_RECEIPT_MISSING",
        payload: { executedAt: 2000, note: "Ledger committed; receipt storage unavailable" },
      },
      expectedStatus: "EXECUTED_RECEIPT_MISSING",
      assertion: (state) => {
        if (state.status === "EXECUTED_RECEIPT_MISSING") {
          expect(state.executedAt).toBe(2000);
          expect(state.note).toContain("Ledger committed");
        }
      },
    },

    // 16. ACCEPTED -> REFUSED on REFUSE_OPERATION
    {
      name: "ACCEPTED -> REFUSED on REFUSE_OPERATION",
      initialState: {
        status: "ACCEPTED",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
        authority: mockAuthority,
        acceptedAt: 1400,
        executionId: "exec-001",
      },
      event: {
        type: "REFUSE_OPERATION",
        payload: { refusal: mockRefusal, refusedAt: 1450 },
      },
      expectedStatus: "REFUSED",
    },

    // 17. ACCEPTED -> FAILED on EXECUTION_FAILED
    {
      name: "ACCEPTED -> FAILED on EXECUTION_FAILED (diagnostic failure)",
      initialState: {
        status: "ACCEPTED",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
        authority: mockAuthority,
        acceptedAt: 1400,
        executionId: "exec-001",
      },
      event: {
        type: "EXECUTION_FAILED",
        payload: { failure: mockFailure, failedAt: 1500 },
      },
      expectedStatus: "FAILED",
      assertion: (state) => {
        if (state.status === "FAILED") {
          expect(state.failure).toEqual(mockFailure);
        }
      },
    },

    // 18. ACCEPTED -> UNKNOWN_COMPLETION on EXECUTION_DISCONNECTED
    {
      name: "ACCEPTED -> UNKNOWN_COMPLETION on network disconnect while executing",
      initialState: {
        status: "ACCEPTED",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
        authority: mockAuthority,
        acceptedAt: 1400,
        executionId: "exec-001",
      },
      event: {
        type: "EXECUTION_DISCONNECTED",
        payload: {
          reason: "HTTP 504 Gateway Timeout during long-running operation",
          disconnectedAt: 1800,
        },
      },
      expectedStatus: "UNKNOWN_COMPLETION",
      assertion: (state) => {
        if (state.status === "UNKNOWN_COMPLETION") {
          expect(state.unknownCompletion.lastKnownStage).toBe("ACCEPTED");
        }
      },
    },

    // 19. EXECUTED_RECEIPT_MISSING -> LATE_VERIFIED_RECEIPT on ATTACH_RECEIPT
    {
      name: "EXECUTED_RECEIPT_MISSING -> LATE_VERIFIED_RECEIPT on ATTACH_RECEIPT",
      initialState: {
        status: "EXECUTED_RECEIPT_MISSING",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
        authority: mockAuthority,
        executedAt: 2000,
      },
      event: {
        type: "ATTACH_RECEIPT",
        payload: { receipt: mockReceipt, attachedAt: 2200 },
      },
      expectedStatus: "LATE_VERIFIED_RECEIPT",
      assertion: (state) => {
        if (state.status === "LATE_VERIFIED_RECEIPT") {
          expect(state.receipt).toEqual(mockReceipt);
          expect(state.attachedAt).toBe(2200);
          expect(state.executedAt).toBe(2000);
        }
      },
    },

    // 20. UNKNOWN_COMPLETION -> LATE_VERIFIED_RECEIPT on late ATTACH_RECEIPT reconciliation
    {
      name: "UNKNOWN_COMPLETION -> LATE_VERIFIED_RECEIPT on reconciliation via ATTACH_RECEIPT",
      initialState: {
        status: "UNKNOWN_COMPLETION",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
        authority: mockAuthority,
        unknownCompletion: {
          reason: "Network timeout",
          disconnectedAt: 1800,
          lastKnownStage: "ACCEPTED",
        },
        lastAttemptedAt: 1800,
      },
      event: {
        type: "ATTACH_RECEIPT",
        payload: { receipt: mockReceipt, attachedAt: 2500 },
      },
      expectedStatus: "LATE_VERIFIED_RECEIPT",
      assertion: (state) => {
        if (state.status === "LATE_VERIFIED_RECEIPT") {
          expect(state.receipt).toEqual(mockReceipt);
          expect(state.attachedAt).toBe(2500);
        }
      },
    },

    // 21. Terminal states -> IDLE on RESET
    {
      name: "EXECUTED -> IDLE on RESET",
      initialState: {
        status: "EXECUTED",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
        authority: mockAuthority,
        receipt: mockReceipt,
        executedAt: 2000,
      },
      event: { type: "RESET" },
      expectedStatus: "IDLE",
    },
    {
      name: "LATE_VERIFIED_RECEIPT -> IDLE on RESET",
      initialState: {
        status: "LATE_VERIFIED_RECEIPT",
        operationId: "op-100",
        params: mockParams,
        preview: mockPreview,
        authority: mockAuthority,
        receipt: mockReceipt,
        executedAt: 2000,
        attachedAt: 2200,
      },
      event: { type: "RESET" },
      expectedStatus: "IDLE",
    },
    {
      name: "FAILED -> IDLE on RESET",
      initialState: {
        status: "FAILED",
        operationId: "op-100",
        failure: mockFailure,
        failedAt: 1500,
      },
      event: { type: "RESET" },
      expectedStatus: "IDLE",
    },
    {
      name: "REFUSED -> IDLE on RESET",
      initialState: {
        status: "REFUSED",
        operationId: "op-100",
        refusal: mockRefusal,
        refusedAt: 1250,
      },
      event: { type: "RESET" },
      expectedStatus: "IDLE",
    },
  ];

  it.each(testCases)("$name", ({ initialState, event, expectedStatus, assertion }) => {
    const nextState = operationReducer(initialState, event);
    expect(nextState.status).toBe(expectedStatus);
    if (assertion) {
      assertion(nextState);
    }
  });
});

describe("operationReducer - Invalidation on Preview Change / Expiry", () => {
  it("transitions to PREVIEW_EXPIRED when REQUEST_AUTHORITY is dispatched after preview expires", () => {
    const expiredPreview: PreviewData = {
      ...mockPreview,
      expiresAt: 2000,
    };
    const state: OperationState = {
      status: "PREVIEWING",
      operationId: "op-100",
      params: mockParams,
      preview: expiredPreview,
    };

    const nextState = operationReducer(state, {
      type: "REQUEST_AUTHORITY",
      payload: { currentTimestamp: 2001, requestedAt: 2001 },
    });

    expect(nextState.status).toBe("PREVIEW_EXPIRED");
    if (nextState.status === "PREVIEW_EXPIRED") {
      expect(nextState.expiredAt).toBe(2001);
    }
  });

  it("transitions to PREVIEW_CHANGED when REQUEST_AUTHORITY detects paramHash mismatch", () => {
    const mismatchedPreview: PreviewData = {
      ...mockPreview,
      paramHash: "outdated-hash-999",
    };
    const state: OperationState = {
      status: "PREVIEWING",
      operationId: "op-100",
      params: mockParams, // has paramHash: "hash-initial-123"
      preview: mismatchedPreview,
    };

    const nextState = operationReducer(state, {
      type: "REQUEST_AUTHORITY",
      payload: { currentTimestamp: 1000 },
    });

    expect(nextState.status).toBe("PREVIEW_CHANGED");
    if (nextState.status === "PREVIEW_CHANGED") {
      expect(nextState.reason).toContain("does not match current parameter hash");
    }
  });

  it("strictly blocks REQUEST_AUTHORITY and AUTHORITY_GRANTED from PREVIEW_EXPIRED", () => {
    const expiredState: OperationState = {
      status: "PREVIEW_EXPIRED",
      operationId: "op-100",
      params: mockParams,
      preview: mockPreview,
      expiredAt: 5500,
    };

    // Attempt request authority from expired state
    const attemptAuthority = operationReducer(expiredState, {
      type: "REQUEST_AUTHORITY",
    });
    expect(attemptAuthority.status).toBe("PREVIEW_EXPIRED");

    // Attempt authority grant from expired state
    const attemptGrant = operationReducer(expiredState, {
      type: "AUTHORITY_GRANTED",
      payload: { authority: mockAuthority },
    });
    expect(attemptGrant.status).toBe("PREVIEW_EXPIRED");

    // Re-requesting preview from expired state successfully transitions back to PREVIEWING
    const rePreview = operationReducer(expiredState, {
      type: "REQUEST_PREVIEW",
      payload: { operationId: "op-100", params: mockParams },
    });
    expect(rePreview.status).toBe("PREVIEWING");
  });

  it("strictly blocks REQUEST_AUTHORITY and AUTHORITY_GRANTED from PREVIEW_CHANGED", () => {
    const changedState: OperationState = {
      status: "PREVIEW_CHANGED",
      operationId: "op-100",
      originalParams: mockParams,
      updatedParams: mockUpdatedParams,
      preview: mockPreview,
      reason: "Parameters changed in background",
    };

    // Attempt request authority from changed state
    const attemptAuthority = operationReducer(changedState, {
      type: "REQUEST_AUTHORITY",
    });
    expect(attemptAuthority.status).toBe("PREVIEW_CHANGED");

    // Attempt authority grant from changed state
    const attemptGrant = operationReducer(changedState, {
      type: "AUTHORITY_GRANTED",
      payload: { authority: mockAuthority },
    });
    expect(attemptGrant.status).toBe("PREVIEW_CHANGED");

    // Re-requesting preview with updated params transitions back to PREVIEWING
    const rePreview = operationReducer(changedState, {
      type: "REQUEST_PREVIEW",
      payload: { operationId: "op-100", params: mockUpdatedParams },
    });
    expect(rePreview.status).toBe("PREVIEWING");
  });
});

describe("operationReducer - Refusal vs Failure Distinction", () => {
  it("records policy/permission refusal distinct from execution failure", () => {
    const queuedState: OperationState = {
      status: "QUEUED",
      operationId: "op-100",
      params: mockParams,
      preview: mockPreview,
      authority: mockAuthority,
      queuedAt: 1300,
    };

    const refusedState = operationReducer(queuedState, {
      type: "REFUSE_OPERATION",
      payload: { refusal: mockRefusal, refusedAt: 1350 },
    });

    const failedState = operationReducer(queuedState, {
      type: "EXECUTION_FAILED",
      payload: { failure: mockFailure, failedAt: 1380 },
    });

    expect(refusedState.status).toBe("REFUSED");
    expect(failedState.status).toBe("FAILED");

    if (refusedState.status === "REFUSED") {
      expect(refusedState.refusal.code).toBe("POLICY_VIOLATION");
      expect(refusedState.refusal.policy).toBe("strict-infra-bounds");
      expect("failure" in refusedState).toBe(false);
    }

    if (failedState.status === "FAILED") {
      expect(failedState.failure.code).toBe("CONTAINER_CRASH");
      expect(failedState.failure.diagnostic).toBeDefined();
      expect("refusal" in failedState).toBe(false);
    }
  });

  it("distinguishes AUTHORITY_REFUSED from operational failure", () => {
    const waitingState: OperationState = {
      status: "WAITING_FOR_AUTHORITY",
      operationId: "op-100",
      params: mockParams,
      preview: mockPreview,
      requestedAt: 1200,
    };

    const refused = operationReducer(waitingState, {
      type: "AUTHORITY_REFUSED",
      payload: { refusal: mockRefusal, refusedAt: 1250 },
    });

    expect(refused.status).toBe("REFUSED");
    expect(isTerminalState(refused)).toBe(true);
  });
});

describe("operationReducer - Explicit Invariant: UNKNOWN_COMPLETION Strict Refusal of Retry", () => {
  const unknownCompletionState: OperationState = Object.freeze({
    status: "UNKNOWN_COMPLETION",
    operationId: "op-100",
    params: mockParams,
    preview: mockPreview,
    authority: mockAuthority,
    unknownCompletion: {
      reason: "Network connection dropped after dispatch ack",
      disconnectedAt: 1800,
      lastKnownStage: "ACCEPTED" as const,
    },
    lastAttemptedAt: 1800,
  });

  it("strictly refuses RETRY event and flags retryAttemptBlocked", () => {
    const nextState = operationReducer(unknownCompletionState, {
      type: "RETRY",
      payload: { retriedAt: 1900 },
    });

    // INVARIANT: Never transitions to QUEUED, ACCEPTED, or PREVIEWING
    expect(nextState.status).toBe("UNKNOWN_COMPLETION");
    if (nextState.status === "UNKNOWN_COMPLETION") {
      expect(nextState.retryAttemptBlocked).toBe(true);
    }
  });

  it("strictly refuses REQUEST_PREVIEW event without prior manual reset", () => {
    const nextState = operationReducer(unknownCompletionState, {
      type: "REQUEST_PREVIEW",
      payload: { operationId: "op-100", params: mockParams },
    });

    expect(nextState.status).toBe("UNKNOWN_COMPLETION");
    if (nextState.status === "UNKNOWN_COMPLETION") {
      expect(nextState.retryAttemptBlocked).toBe(true);
    }
  });

  it("strictly refuses AUTHORITY_GRANTED or ACCEPT_OPERATION", () => {
    const grantedAttempt = operationReducer(unknownCompletionState, {
      type: "AUTHORITY_GRANTED",
      payload: { authority: mockAuthority },
    });
    expect(grantedAttempt.status).toBe("UNKNOWN_COMPLETION");

    const acceptAttempt = operationReducer(unknownCompletionState, {
      type: "ACCEPT_OPERATION",
    });
    expect(acceptAttempt.status).toBe("UNKNOWN_COMPLETION");
  });

  it("canRetry helper strictly returns false for UNKNOWN_COMPLETION", () => {
    expect(canRetry(unknownCompletionState)).toBe(false);

    // Contrast with FAILED or REFUSED which can be safely re-previewed
    const failedState: OperationState = {
      status: "FAILED",
      operationId: "op-100",
      failure: mockFailure,
      failedAt: 1500,
    };
    expect(canRetry(failedState)).toBe(true);
  });

  it("only safely resolves UNKNOWN_COMPLETION via ATTACH_RECEIPT or manual RESET", () => {
    // 1. Reconciliation when proof/receipt is found
    const reconciledState = operationReducer(unknownCompletionState, {
      type: "ATTACH_RECEIPT",
      payload: { receipt: mockReceipt, attachedAt: 2500 },
    });
    expect(reconciledState.status).toBe("LATE_VERIFIED_RECEIPT");
    expect(isReceiptVerified(reconciledState)).toBe(true);

    // 2. Manual operator reset to IDLE
    const resetState = operationReducer(unknownCompletionState, { type: "RESET" });
    expect(resetState.status).toBe("IDLE");
  });
});

describe("operationReducer - Immutability and Pure Reducer Discipline", () => {
  it("never mutates input state and returns frozen immutable object", () => {
    const initial = Object.freeze({
      status: "PREVIEWING" as const,
      operationId: "op-100",
      params: Object.freeze(mockParams),
      preview: Object.freeze(mockPreview),
    });

    const next = operationReducer(initial, {
      type: "REQUEST_AUTHORITY",
      payload: { currentTimestamp: 1000, requestedAt: 1000 },
    });

    expect(next).not.toBe(initial);
    expect(Object.isFrozen(next)).toBe(true);
    // Initial state remains untouched
    expect(initial.status).toBe("PREVIEWING");
  });

  it("returns unmodified state reference on invalid / no-op events", () => {
    const state: OperationState = {
      status: "IDLE",
    };

    // PREVIEW_READY is invalid while IDLE
    const nextState = operationReducer(state, {
      type: "PREVIEW_READY",
      payload: { preview: mockPreview },
    });

    expect(nextState).toBe(state);
  });

  it("does not allow RESET while operation is actively QUEUED or ACCEPTED in flight", () => {
    const queuedState: OperationState = {
      status: "QUEUED",
      operationId: "op-100",
      params: mockParams,
      preview: mockPreview,
      authority: mockAuthority,
      queuedAt: 1300,
    };

    const nextQueued = operationReducer(queuedState, { type: "RESET" });
    expect(nextQueued.status).toBe("QUEUED");
    expect(nextQueued).toBe(queuedState);

    const acceptedState: OperationState = {
      status: "ACCEPTED",
      operationId: "op-100",
      params: mockParams,
      preview: mockPreview,
      authority: mockAuthority,
      acceptedAt: 1400,
    };

    const nextAccepted = operationReducer(acceptedState, { type: "RESET" });
    expect(nextAccepted.status).toBe("ACCEPTED");
    expect(nextAccepted).toBe(acceptedState);
  });
});

describe("State Query Helpers", () => {
  it("evaluates isTerminalState correctly", () => {
    expect(isTerminalState(INITIAL_OPERATION_STATE)).toBe(false);
    expect(
      isTerminalState({
        status: "EXECUTED",
        operationId: "op-1",
        params: mockParams,
        preview: mockPreview,
        authority: mockAuthority,
        receipt: mockReceipt,
        executedAt: 1000,
      }),
    ).toBe(true);
    expect(
      isTerminalState({
        status: "LATE_VERIFIED_RECEIPT",
        operationId: "op-1",
        params: mockParams,
        preview: mockPreview,
        authority: mockAuthority,
        receipt: mockReceipt,
        executedAt: 1000,
        attachedAt: 1100,
      }),
    ).toBe(true);
    expect(
      isTerminalState({
        status: "REFUSED",
        operationId: "op-1",
        refusal: mockRefusal,
        refusedAt: 1000,
      }),
    ).toBe(true);
    expect(
      isTerminalState({
        status: "FAILED",
        operationId: "op-1",
        failure: mockFailure,
        failedAt: 1000,
      }),
    ).toBe(true);
    expect(
      isTerminalState({
        status: "UNKNOWN_COMPLETION",
        operationId: "op-1",
        params: mockParams,
        preview: mockPreview,
        authority: mockAuthority,
        unknownCompletion: {
          reason: "timeout",
          disconnectedAt: 1000,
          lastKnownStage: "ACCEPTED",
        },
        lastAttemptedAt: 1000,
      }),
    ).toBe(false);
  });

  it("evaluates canRequestAuthority and isWaitingForAuthority correctly", () => {
    expect(canRequestAuthority(INITIAL_OPERATION_STATE)).toBe(false);
    expect(
      canRequestAuthority({
        status: "PREVIEWING",
        operationId: "op-1",
        params: mockParams,
      }),
    ).toBe(false);
    expect(
      canRequestAuthority({
        status: "PREVIEWING",
        operationId: "op-1",
        params: mockParams,
        preview: mockPreview,
      }),
    ).toBe(true);

    expect(
      isWaitingForAuthority({
        status: "WAITING_FOR_AUTHORITY",
        operationId: "op-1",
        params: mockParams,
        preview: mockPreview,
        requestedAt: 500,
      }),
    ).toBe(true);
  });
});
