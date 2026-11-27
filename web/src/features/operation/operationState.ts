/**
 * Operation Lifecycle Reducer
 *
 * Implements the operation state machine as a pure TypeScript reducer.
 * Requirements:
 * - Pure reducer function: operationReducer(state, event)
 * - Zero side effects, zero network calls, immutable transitions (never mutate state).
 * - Explicit Invariant: UNKNOWN_COMPLETION never allows automatic retry.
 * - Explicit Invalidation: preview changes or expirations invalidate apply.
 * - Explicit Distinction: REFUSED (policy/permission denial) vs FAILED (execution diagnostic error).
 */

export type OperationStatus =
  | "IDLE"
  | "PREVIEWING"
  | "PREVIEW_EXPIRED"
  | "PREVIEW_CHANGED"
  | "WAITING_FOR_AUTHORITY"
  | "QUEUED"
  | "ACCEPTED"
  | "EXECUTED"
  | "REFUSED"
  | "FAILED"
  | "UNKNOWN_COMPLETION"
  | "EXECUTED_RECEIPT_MISSING"
  | "LATE_VERIFIED_RECEIPT";

export interface OperationParams {
  readonly operationId: string;
  readonly action: string;
  readonly payload: Readonly<Record<string, unknown>>;
  readonly paramHash: string;
}

export interface PreviewData {
  readonly previewId: string;
  readonly paramHash: string;
  readonly estimatedCost?: number | string;
  readonly summary?: string;
  readonly expiresAt?: number;
}

export interface AuthorityProof {
  readonly proofId: string;
  readonly authorizedBy: string;
  readonly timestamp: number;
  readonly signature?: string;
}

export interface OperationReceipt {
  readonly receiptId: string;
  readonly timestamp: number;
  readonly signature?: string;
  readonly details?: Readonly<Record<string, unknown>>;
}

export interface RefusalInfo {
  readonly code: string;
  readonly reason: string;
  readonly policy?: string;
}

export interface DiagnosticFailureInfo {
  readonly code: string;
  readonly reason: string;
  readonly diagnostic?: string;
  readonly stack?: string;
}

export interface UnknownCompletionInfo {
  readonly reason: string;
  readonly disconnectedAt: number;
  readonly lastKnownStage: "QUEUED" | "ACCEPTED";
  readonly details?: string;
}

/* =========================================================================
   State Interfaces (Discriminated Union on `status`)
   ========================================================================= */

export interface IdleState {
  readonly status: "IDLE";
}

export interface PreviewingState {
  readonly status: "PREVIEWING";
  readonly operationId: string;
  readonly params: OperationParams;
  readonly preview?: PreviewData;
}

export interface PreviewExpiredState {
  readonly status: "PREVIEW_EXPIRED";
  readonly operationId: string;
  readonly params: OperationParams;
  readonly preview: PreviewData;
  readonly expiredAt: number;
}

export interface PreviewChangedState {
  readonly status: "PREVIEW_CHANGED";
  readonly operationId: string;
  readonly originalParams: OperationParams;
  readonly updatedParams: OperationParams;
  readonly preview?: PreviewData;
  readonly reason: string;
}

export interface WaitingForAuthorityState {
  readonly status: "WAITING_FOR_AUTHORITY";
  readonly operationId: string;
  readonly params: OperationParams;
  readonly preview: PreviewData;
  readonly requestedAt: number;
}

export interface QueuedState {
  readonly status: "QUEUED";
  readonly operationId: string;
  readonly params: OperationParams;
  readonly preview: PreviewData;
  readonly authority: AuthorityProof;
  readonly queuedAt: number;
}

export interface AcceptedState {
  readonly status: "ACCEPTED";
  readonly operationId: string;
  readonly params: OperationParams;
  readonly preview: PreviewData;
  readonly authority: AuthorityProof;
  readonly acceptedAt: number;
  readonly executionId?: string;
}

export interface ExecutedState {
  readonly status: "EXECUTED";
  readonly operationId: string;
  readonly params: OperationParams;
  readonly preview: PreviewData;
  readonly authority: AuthorityProof;
  readonly receipt: OperationReceipt;
  readonly executedAt: number;
}

export interface RefusedState {
  readonly status: "REFUSED";
  readonly operationId: string;
  readonly refusal: RefusalInfo;
  readonly params?: OperationParams;
  readonly preview?: PreviewData;
  readonly refusedAt: number;
}

export interface FailedState {
  readonly status: "FAILED";
  readonly operationId: string;
  readonly failure: DiagnosticFailureInfo;
  readonly params?: OperationParams;
  readonly preview?: PreviewData;
  readonly failedAt: number;
}

export interface UnknownCompletionState {
  readonly status: "UNKNOWN_COMPLETION";
  readonly operationId: string;
  readonly params: OperationParams;
  readonly preview: PreviewData;
  readonly authority: AuthorityProof;
  readonly unknownCompletion: UnknownCompletionInfo;
  readonly lastAttemptedAt: number;
  readonly retryAttemptBlocked?: boolean;
}

export interface ExecutedReceiptMissingState {
  readonly status: "EXECUTED_RECEIPT_MISSING";
  readonly operationId: string;
  readonly params: OperationParams;
  readonly preview: PreviewData;
  readonly authority: AuthorityProof;
  readonly executedAt: number;
  readonly note?: string;
}

export interface LateVerifiedReceiptState {
  readonly status: "LATE_VERIFIED_RECEIPT";
  readonly operationId: string;
  readonly params: OperationParams;
  readonly preview: PreviewData;
  readonly authority: AuthorityProof;
  readonly receipt: OperationReceipt;
  readonly executedAt: number;
  readonly attachedAt: number;
}

export type OperationState =
  | IdleState
  | PreviewingState
  | PreviewExpiredState
  | PreviewChangedState
  | WaitingForAuthorityState
  | QueuedState
  | AcceptedState
  | ExecutedState
  | RefusedState
  | FailedState
  | UnknownCompletionState
  | ExecutedReceiptMissingState
  | LateVerifiedReceiptState;

export const INITIAL_OPERATION_STATE: IdleState = Object.freeze({
  status: "IDLE",
});

/* =========================================================================
   Event Interfaces (Discriminated Union on `type`)
   ========================================================================= */

export interface RequestPreviewEvent {
  readonly type: "REQUEST_PREVIEW";
  readonly payload: {
    readonly operationId: string;
    readonly params: OperationParams;
  };
}

export interface PreviewReadyEvent {
  readonly type: "PREVIEW_READY";
  readonly payload: {
    readonly preview: PreviewData;
  };
}

export interface ParamsChangedEvent {
  readonly type: "PARAMS_CHANGED";
  readonly payload: {
    readonly updatedParams: OperationParams;
    readonly reason?: string;
  };
}

export interface PreviewExpiredEvent {
  readonly type: "PREVIEW_EXPIRED";
  readonly payload?: {
    readonly expiredAt?: number;
  };
}

export interface RequestAuthorityEvent {
  readonly type: "REQUEST_AUTHORITY";
  readonly payload?: {
    readonly requestedAt?: number;
    readonly currentTimestamp?: number;
  };
}

export interface AuthorityGrantedEvent {
  readonly type: "AUTHORITY_GRANTED";
  readonly payload: {
    readonly authority: AuthorityProof;
    readonly queuedAt?: number;
    readonly currentTimestamp?: number;
  };
}

export interface AuthorityRefusedEvent {
  readonly type: "AUTHORITY_REFUSED";
  readonly payload: {
    readonly refusal: RefusalInfo;
    readonly refusedAt?: number;
  };
}

export interface AcceptOperationEvent {
  readonly type: "ACCEPT_OPERATION";
  readonly payload?: {
    readonly acceptedAt?: number;
    readonly executionId?: string;
  };
}

export interface RefuseOperationEvent {
  readonly type: "REFUSE_OPERATION";
  readonly payload: {
    readonly refusal: RefusalInfo;
    readonly refusedAt?: number;
  };
}

export interface ExecutionSucceededEvent {
  readonly type: "EXECUTION_SUCCEEDED";
  readonly payload: {
    readonly receipt: OperationReceipt;
    readonly executedAt?: number;
  };
}

export interface ExecutionConfirmedReceiptMissingEvent {
  readonly type: "EXECUTION_CONFIRMED_RECEIPT_MISSING";
  readonly payload?: {
    readonly executedAt?: number;
    readonly note?: string;
  };
}

export interface ExecutionFailedEvent {
  readonly type: "EXECUTION_FAILED";
  readonly payload: {
    readonly failure: DiagnosticFailureInfo;
    readonly failedAt?: number;
  };
}

export interface ExecutionDisconnectedEvent {
  readonly type: "EXECUTION_DISCONNECTED";
  readonly payload: {
    readonly reason: string;
    readonly disconnectedAt?: number;
    readonly details?: string;
  };
}

export interface AttachReceiptEvent {
  readonly type: "ATTACH_RECEIPT";
  readonly payload: {
    readonly receipt: OperationReceipt;
    readonly attachedAt?: number;
  };
}

export interface RetryEvent {
  readonly type: "RETRY";
  readonly payload?: {
    readonly retriedAt?: number;
  };
}

export interface ResetEvent {
  readonly type: "RESET";
}

export type OperationEvent =
  | RequestPreviewEvent
  | PreviewReadyEvent
  | ParamsChangedEvent
  | PreviewExpiredEvent
  | RequestAuthorityEvent
  | AuthorityGrantedEvent
  | AuthorityRefusedEvent
  | AcceptOperationEvent
  | RefuseOperationEvent
  | ExecutionSucceededEvent
  | ExecutionConfirmedReceiptMissingEvent
  | ExecutionFailedEvent
  | ExecutionDisconnectedEvent
  | AttachReceiptEvent
  | RetryEvent
  | ResetEvent;

/* =========================================================================
   Pure Reducer Function
   ========================================================================= */

/**
 * Pure reducer for the operation lifecycle state machine.
 * Guaranteed to have zero side effects, zero network calls, and strict immutability.
 */
export function operationReducer(
  state: OperationState,
  event: OperationEvent,
): OperationState {
  switch (event.type) {
    case "REQUEST_PREVIEW": {
      // In flight or executing states cannot be re-previewed directly.
      if (
        state.status === "QUEUED" ||
        state.status === "ACCEPTED" ||
        state.status === "EXECUTED_RECEIPT_MISSING"
      ) {
        return state;
      }

      // CRITICAL INVARIANT: UNKNOWN_COMPLETION strictly forbids re-preview / retry
      // without explicit manual reset.
      if (state.status === "UNKNOWN_COMPLETION") {
        return Object.freeze({
          ...state,
          retryAttemptBlocked: true,
        });
      }

      const { operationId, params } = event.payload;
      return Object.freeze({
        status: "PREVIEWING",
        operationId,
        params,
      });
    }

    case "PREVIEW_READY": {
      if (state.status !== "PREVIEWING") {
        return state;
      }
      return Object.freeze({
        ...state,
        preview: event.payload.preview,
      });
    }

    case "PARAMS_CHANGED": {
      const { updatedParams, reason = "Parameters changed" } = event.payload;

      switch (state.status) {
        case "PREVIEWING": {
          return Object.freeze({
            status: "PREVIEW_CHANGED",
            operationId: state.operationId,
            originalParams: state.params,
            updatedParams,
            preview: state.preview,
            reason,
          });
        }
        case "WAITING_FOR_AUTHORITY": {
          // Invalidate authority request when underlying parameters change
          return Object.freeze({
            status: "PREVIEW_CHANGED",
            operationId: state.operationId,
            originalParams: state.params,
            updatedParams,
            preview: state.preview,
            reason,
          });
        }
        case "PREVIEW_EXPIRED": {
          return Object.freeze({
            status: "PREVIEW_CHANGED",
            operationId: state.operationId,
            originalParams: state.params,
            updatedParams,
            preview: state.preview,
            reason,
          });
        }
        case "PREVIEW_CHANGED": {
          return Object.freeze({
            ...state,
            updatedParams,
            reason,
          });
        }
        default:
          return state;
      }
    }

    case "PREVIEW_EXPIRED": {
      const expiredAt = event.payload?.expiredAt ?? 0;

      if (state.status === "PREVIEWING" && state.preview) {
        return Object.freeze({
          status: "PREVIEW_EXPIRED",
          operationId: state.operationId,
          params: state.params,
          preview: state.preview,
          expiredAt,
        });
      }

      if (state.status === "WAITING_FOR_AUTHORITY") {
        return Object.freeze({
          status: "PREVIEW_EXPIRED",
          operationId: state.operationId,
          params: state.params,
          preview: state.preview,
          expiredAt,
        });
      }

      return state;
    }

    case "REQUEST_AUTHORITY": {
      // Cannot request authority if expired or changed
      if (state.status === "PREVIEW_EXPIRED" || state.status === "PREVIEW_CHANGED") {
        return state;
      }

      if (state.status !== "PREVIEWING") {
        return state;
      }

      // Preview must have been generated
      if (!state.preview) {
        return state;
      }

      const now = event.payload?.currentTimestamp ?? 0;
      const requestedAt = event.payload?.requestedAt ?? now;

      // Invalidation check: if preview expired by timestamp
      if (state.preview.expiresAt !== undefined && now > state.preview.expiresAt) {
        return Object.freeze({
          status: "PREVIEW_EXPIRED",
          operationId: state.operationId,
          params: state.params,
          preview: state.preview,
          expiredAt: now,
        });
      }

      // Invalidation check: paramHash mismatch
      if (state.preview.paramHash !== state.params.paramHash) {
        return Object.freeze({
          status: "PREVIEW_CHANGED",
          operationId: state.operationId,
          originalParams: state.params,
          updatedParams: state.params,
          preview: state.preview,
          reason: "Preview hash does not match current parameter hash",
        });
      }

      return Object.freeze({
        status: "WAITING_FOR_AUTHORITY",
        operationId: state.operationId,
        params: state.params,
        preview: state.preview,
        requestedAt,
      });
    }

    case "AUTHORITY_GRANTED": {
      if (state.status !== "WAITING_FOR_AUTHORITY") {
        return state;
      }

      const now = event.payload.currentTimestamp ?? 0;
      const queuedAt = event.payload.queuedAt ?? now;

      // Guard: if preview expired while waiting for authority
      if (state.preview.expiresAt !== undefined && now > state.preview.expiresAt) {
        return Object.freeze({
          status: "PREVIEW_EXPIRED",
          operationId: state.operationId,
          params: state.params,
          preview: state.preview,
          expiredAt: now,
        });
      }

      return Object.freeze({
        status: "QUEUED",
        operationId: state.operationId,
        params: state.params,
        preview: state.preview,
        authority: event.payload.authority,
        queuedAt,
      });
    }

    case "AUTHORITY_REFUSED": {
      if (state.status !== "WAITING_FOR_AUTHORITY") {
        return state;
      }

      return Object.freeze({
        status: "REFUSED",
        operationId: state.operationId,
        params: state.params,
        preview: state.preview,
        refusal: event.payload.refusal,
        refusedAt: event.payload.refusedAt ?? 0,
      });
    }

    case "ACCEPT_OPERATION": {
      if (state.status !== "QUEUED") {
        return state;
      }

      return Object.freeze({
        status: "ACCEPTED",
        operationId: state.operationId,
        params: state.params,
        preview: state.preview,
        authority: state.authority,
        acceptedAt: event.payload?.acceptedAt ?? 0,
        executionId: event.payload?.executionId,
      });
    }

    case "REFUSE_OPERATION": {
      if (state.status !== "QUEUED" && state.status !== "ACCEPTED") {
        return state;
      }

      return Object.freeze({
        status: "REFUSED",
        operationId: state.operationId,
        params: state.params,
        preview: state.preview,
        refusal: event.payload.refusal,
        refusedAt: event.payload.refusedAt ?? 0,
      });
    }

    case "EXECUTION_SUCCEEDED": {
      if (state.status !== "ACCEPTED") {
        return state;
      }

      return Object.freeze({
        status: "EXECUTED",
        operationId: state.operationId,
        params: state.params,
        preview: state.preview,
        authority: state.authority,
        receipt: event.payload.receipt,
        executedAt: event.payload.executedAt ?? 0,
      });
    }

    case "EXECUTION_CONFIRMED_RECEIPT_MISSING": {
      if (state.status !== "ACCEPTED") {
        return state;
      }

      return Object.freeze({
        status: "EXECUTED_RECEIPT_MISSING",
        operationId: state.operationId,
        params: state.params,
        preview: state.preview,
        authority: state.authority,
        executedAt: event.payload?.executedAt ?? 0,
        note: event.payload?.note,
      });
    }

    case "EXECUTION_FAILED": {
      if (state.status !== "QUEUED" && state.status !== "ACCEPTED") {
        return state;
      }

      return Object.freeze({
        status: "FAILED",
        operationId: state.operationId,
        params: state.params,
        preview: state.preview,
        failure: event.payload.failure,
        failedAt: event.payload.failedAt ?? 0,
      });
    }

    case "EXECUTION_DISCONNECTED": {
      if (state.status !== "QUEUED" && state.status !== "ACCEPTED") {
        return state;
      }

      const lastKnownStage = state.status;
      const disconnectedAt = event.payload.disconnectedAt ?? 0;

      return Object.freeze({
        status: "UNKNOWN_COMPLETION",
        operationId: state.operationId,
        params: state.params,
        preview: state.preview,
        authority: state.authority,
        unknownCompletion: {
          reason: event.payload.reason,
          disconnectedAt,
          lastKnownStage,
          details: event.payload.details,
        },
        lastAttemptedAt: disconnectedAt,
      });
    }

    case "ATTACH_RECEIPT": {
      if (state.status === "EXECUTED_RECEIPT_MISSING") {
        return Object.freeze({
          status: "LATE_VERIFIED_RECEIPT",
          operationId: state.operationId,
          params: state.params,
          preview: state.preview,
          authority: state.authority,
          receipt: event.payload.receipt,
          executedAt: state.executedAt,
          attachedAt: event.payload.attachedAt ?? 0,
        });
      }

      // Reconciliation path for UNKNOWN_COMPLETION if confirmed receipt emerges
      if (state.status === "UNKNOWN_COMPLETION") {
        return Object.freeze({
          status: "LATE_VERIFIED_RECEIPT",
          operationId: state.operationId,
          params: state.params,
          preview: state.preview,
          authority: state.authority,
          receipt: event.payload.receipt,
          executedAt: state.lastAttemptedAt,
          attachedAt: event.payload.attachedAt ?? 0,
        });
      }

      return state;
    }

    case "RETRY": {
      // EXPLICIT INVARIANT: UNKNOWN_COMPLETION NEVER allows automatic retry!
      // Automatic retry could cause dangerous double execution on disconnected systems.
      if (state.status === "UNKNOWN_COMPLETION") {
        return Object.freeze({
          ...state,
          retryAttemptBlocked: true,
        });
      }

      // From FAILED or REFUSED, retrying safely returns to PREVIEWING
      if (state.status === "FAILED" || state.status === "REFUSED") {
        if (!state.params) {
          return INITIAL_OPERATION_STATE;
        }
        return Object.freeze({
          status: "PREVIEWING",
          operationId: state.operationId,
          params: state.params,
        });
      }

      return state;
    }

    case "RESET": {
      // Active in-flight processing should not be arbitrarily wiped
      if (state.status === "QUEUED" || state.status === "ACCEPTED") {
        return state;
      }
      return INITIAL_OPERATION_STATE;
    }

    default: {
      const _exhaustiveCheck: never = event;
      return state;
    }
  }
}

/* =========================================================================
   Inspection & Invariant Query Helpers
   ========================================================================= */

/**
 * Returns true if the operation is in a terminal state.
 */
export function isTerminalState(state: OperationState): boolean {
  return (
    state.status === "EXECUTED" ||
    state.status === "LATE_VERIFIED_RECEIPT" ||
    state.status === "REFUSED" ||
    state.status === "FAILED"
  );
}

/**
 * Strict safety check for retry allowance.
 * GUARANTEES: Never returns true for UNKNOWN_COMPLETION.
 */
export function canRetry(state: OperationState): boolean {
  if (state.status === "UNKNOWN_COMPLETION") {
    return false;
  }
  return state.status === "FAILED" || state.status === "REFUSED";
}

/**
 * Checks if the state indicates a confirmed receipt has been verified.
 */
export function isReceiptVerified(state: OperationState): boolean {
  return state.status === "EXECUTED" || state.status === "LATE_VERIFIED_RECEIPT";
}

/**
 * Checks if the state is awaiting human proof.
 */
export function isWaitingForAuthority(state: OperationState): boolean {
  return state.status === "WAITING_FOR_AUTHORITY";
}

/**
 * Checks whether authority can be requested from the current state.
 */
export function canRequestAuthority(state: OperationState): boolean {
  return state.status === "PREVIEWING" && state.preview !== undefined;
}
