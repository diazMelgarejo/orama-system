import type { ReactElement } from "react";

import type { StatusTone } from "./StatusBadge";
import { statusToTone } from "./statusTone";

/**
 * Operator-facing status states. Text plus icon is the contract: colour never
 * carries the meaning on its own.
 */
export type StatusPillState =
  | "success"
  | "failed"
  | "partial"
  | "waiting"
  | "waiting_authority"
  | "queued"
  | "running"
  | "unknown"
  | "neutral";

export type StatusPillSize = "sm" | "md";

interface PillSpec {
  /** Status token resolved through statusToTone, so tone logic stays in one place. */
  readonly status: string;
  readonly label: string;
}

const PILL_SPECS: Record<StatusPillState, PillSpec> = {
  success: { status: "ok", label: "Success" },
  failed: { status: "failed", label: "Failed" },
  partial: { status: "partial", label: "Partial" },
  waiting: { status: "waiting", label: "Waiting" },
  waiting_authority: { status: "waiting", label: "Waiting for authority" },
  queued: { status: "queued", label: "Queued" },
  running: { status: "running", label: "Running" },
  unknown: { status: "unknown", label: "Unknown" },
  neutral: { status: "", label: "Neutral" },
};

/** Soft tint plus emphasised text, expressed only with existing token classes. */
const TONE_CLASSES: Record<StatusTone, string> = {
  ok: "bg-status-ok/15 text-status-ok ring-status-ok/30",
  err: "bg-status-err/15 text-status-err ring-status-err/30",
  warn: "bg-status-warn/15 text-status-warn ring-status-warn/30",
  info: "bg-status-info/15 text-status-info ring-status-info/30",
  gpu: "bg-status-gpu/15 text-status-gpu ring-status-gpu/30",
  neutral: "bg-canvas-raised text-ink-muted ring-line",
};

/** text-xs is 0.75rem and text-sm is 0.875rem: nothing smaller is allowed here. */
const SIZE_CLASSES: Record<StatusPillSize, string> = {
  sm: "gap-1 px-2 py-0.5 text-xs",
  md: "gap-1.5 px-2.5 py-1 text-sm",
};

const ICON_CONTENT: Record<StatusPillState, ReactElement> = {
  success: <path d="M2.75 6.4 5.1 8.75 9.25 3.6" />,
  failed: (
    <>
      <path d="M3.25 3.25 8.75 8.75" />
      <path d="M8.75 3.25 3.25 8.75" />
    </>
  ),
  partial: (
    <>
      <circle cx="6" cy="6" r="3.75" />
      <path d="M6 2.25A3.75 3.75 0 0 1 6 9.75Z" fill="currentColor" stroke="none" />
    </>
  ),
  waiting: (
    <>
      <circle cx="6" cy="6" r="4" />
      <path d="M6 3.5V6l1.75 1.25" />
    </>
  ),
  waiting_authority: (
    <>
      <rect x="2.75" y="5.25" width="6.5" height="4.5" rx="1" />
      <path d="M4.5 5.25V4a1.5 1.5 0 0 1 3 0v1.25" />
    </>
  ),
  queued: (
    <>
      <path d="M2.5 3.5h7" />
      <path d="M2.5 6h7" />
      <path d="M2.5 8.5h3.5" />
    </>
  ),
  running: <path d="M4.25 2.9 9 6l-4.75 3.1Z" fill="currentColor" stroke="none" />,
  unknown: <circle cx="6" cy="6" r="3.9" strokeDasharray="2 2" />,
  neutral: <path d="M3 6h6" />,
};

interface StatusPillIconProps {
  readonly state: StatusPillState;
}

function StatusPillIcon({ state }: StatusPillIconProps) {
  return (
    <svg
      viewBox="0 0 12 12"
      className="h-3 w-3 shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      data-icon={state}
    >
      {ICON_CONTENT[state]}
    </svg>
  );
}

export interface StatusPillProps {
  readonly state: StatusPillState;
  readonly size?: StatusPillSize;
  readonly className?: string;
}

export function StatusPill({ state, size = "sm", className = "" }: StatusPillProps) {
  const spec = PILL_SPECS[state];
  const tone = statusToTone(spec.status);

  return (
    <span
      data-state={state}
      data-tone={tone}
      className={`inline-flex items-center whitespace-nowrap rounded-sm font-mono font-medium tracking-wide ring-1 ring-inset ${SIZE_CLASSES[size]} ${TONE_CLASSES[tone]} ${className}`}
    >
      <StatusPillIcon state={state} />
      <span>{spec.label}</span>
    </span>
  );
}
