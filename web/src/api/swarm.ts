import { apiFetch } from "./client";

export type TaskType = "implementation" | "coding" | "reasoning" | "research" | "ops";
export type OptimizeFor = "speed" | "quality" | "reliability";
export type PreferredDevice = "mac" | "windows" | "shared" | "auto";

export interface SwarmPreviewRequest {
  objective: string;
  task_type?: TaskType;
  optimize_for?: OptimizeFor;
  preferred_device?: PreferredDevice;
}

export interface SwarmLaunchRequest extends SwarmPreviewRequest {
  approved: true;
  preview_id: string;
  approval_token: string;
}

export interface SwarmAssignment {
  role: string;
  specialization: string;
  intent: string;
  backend_hint: string | null;
  model_hint?: string | null;
  expected_output_shape: string;
  verification_rubric: string;
  routing_source: string;
  routing_error?: string;
  dispatch_allowed?: boolean;
}

export interface HardwarePolicyViolation {
  role?: string;
  model?: string;
  reason?: string;
  message?: string;
  [k: string]: unknown;
}

export interface HardwarePolicyResult {
  ok: boolean;
  violations: Array<string | HardwarePolicyViolation>;
}

export interface SwarmPreview {
  objective: string;
  task_type: TaskType;
  optimize_for: OptimizeFor;
  preferred_device: PreferredDevice;
  assignments: SwarmAssignment[];
  hardware_policy: HardwarePolicyResult;
  preview_id: string;
  approval_token: string;
  strict_mode: boolean;
  [k: string]: unknown;
}

export interface SwarmLaunchAcceptedJob {
  role: string;
  job_id?: string;
}

export interface SwarmLaunchResult {
  accepted: boolean;
  blocked: boolean;
  session_id: string;
  accepted_jobs: SwarmLaunchAcceptedJob[];
  failed_jobs: Array<{ role: string; error: string }>;
  preview: Omit<SwarmPreview, "preview_id" | "approval_token" | "strict_mode">;
}

export const previewSwarm = (req: SwarmPreviewRequest, signal?: AbortSignal) =>
  apiFetch<SwarmPreview>("/api/swarm/preview", {
    method: "POST",
    body: req,
    signal,
  });

export const launchSwarm = (req: SwarmLaunchRequest, signal?: AbortSignal) =>
  apiFetch<SwarmLaunchResult>("/api/swarm/launch", {
    method: "POST",
    body: req,
    signal,
  });
