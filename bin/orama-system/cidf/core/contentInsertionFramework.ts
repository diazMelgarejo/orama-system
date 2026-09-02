/**
 * contentInsertionFramework.ts
 * ─────────────────────────────
 * Platform-agnostic TypeScript library for Content Insertion Decision Framework v1.3.
 * All TypeScript-based integrations (OpenClaw, etc.) import from here.
 *
 * No runtime dependencies required.
 */

export type TaskType = "content_insertion" | "automation" | "data_processing";
export type FormatRequirement = "plain" | "rich_text" | "strict_layout";
export type ToolName =
  | "direct_form_input"
  | "direct_typing"
  | "clipboard_paste"
  | "file_upload"
  | "scripting";

export interface Task {
  task_type: TaskType;
  is_one_time: boolean;
  frequency_estimate: number;
  content_static: boolean;
  requires_transformation: boolean;
  requires_conditional_logic: boolean;
  requires_external_integration: boolean;
  content_length_chars: number;
  format_requirements: FormatRequirement;
  signature: string;
  estimated_setup_seconds?: number | null;
  estimated_run_seconds?: number | null;
}

export interface Env {
  field_accessible: boolean;
  editor_visible: boolean;
  paste_supported: boolean;
  upload_available: boolean;
  max_safe_chars_form_input?: number;
  max_safe_chars_typing?: number;
  formatting_preserved_on_paste?: boolean;
}

export interface Decision {
  chosen_tool: ToolName | null;
  fallback_chain: ToolName[];
  reason_codes: string[];
  automation_justified: boolean;
  verification_required: true;
  blocked?: boolean;
  notification_reason?: string;
}

export interface Verifier {
  refreshOnceIfNeeded(): Promise<void>;
  extractText(): Promise<string>;
}

export interface AttemptLog {
  tool: ToolName;
  result:
    | "success"
    | "execution_failed"
    | "verification_failed"
    | "verification_error"
    | "no_executor_registered";
  detail?: string;
}

export interface ExecutionResult {
  status: "success" | "failed" | "blocked";
  tool?: ToolName;
  attempts: AttemptLog[];
  notification_reason?: string;
}

export function automationJustified(task: Task): boolean {
  if (task.is_one_time && task.content_static) return false;
  if (
    task.estimated_setup_seconds != null &&
    task.estimated_run_seconds != null &&
    task.estimated_setup_seconds > task.estimated_run_seconds
  ) {
    return false;
  }
  return (
    task.frequency_estimate >= 5 ||
    task.requires_conditional_logic ||
    task.requires_transformation ||
    task.requires_external_integration
  );
}

export function decide(task: Task, env: Env): Decision {
  const maxForm = env.max_safe_chars_form_input ?? 10_000;
  const maxTyping = env.max_safe_chars_typing ?? 5_000;

  const eligibleRanked: ToolName[] = [
    ...(env.field_accessible && task.content_length_chars <= maxForm
      ? (["direct_form_input"] as const)
      : []),
    ...(env.editor_visible && task.content_length_chars <= maxTyping
      ? (["direct_typing"] as const)
      : []),
    ...(env.paste_supported ? (["clipboard_paste"] as const) : []),
    ...(env.upload_available ? (["file_upload"] as const) : []),
  ];

  const justified = automationJustified(task);
  if (eligibleRanked.length > 0) {
    const tools: ToolName[] = justified
      ? [...eligibleRanked, "scripting"]
      : eligibleRanked;
    const chosen = tools[0];
    if (chosen === undefined) {
      // Unreachable given eligibleRanked.length > 0 above, but
      // noUncheckedIndexedAccess correctly can't prove that statically --
      // fail loudly rather than silently return an invalid Decision.
      throw new Error("CIDF internal error: eligible tools list was unexpectedly empty");
    }
    const reasons: string[] = [
      ...(justified ? ["scripting_deferred_until_lower_ranks_exhausted"] : []),
      "chosen_" + chosen,
      "automation_justified=" + justified,
    ];
    return {
      chosen_tool: chosen,
      fallback_chain: tools.slice(1),
      reason_codes: reasons,
      automation_justified: justified,
      verification_required: true,
    };
  }

  if (justified) {
    return {
      chosen_tool: "scripting",
      fallback_chain: [],
      reason_codes: ["chosen_scripting", "automation_justified=True"],
      automation_justified: true,
      verification_required: true,
    };
  }

  const notificationReason = "no_eligible_method_and_automation_gate_closed";
  return {
    chosen_tool: null,
    fallback_chain: [],
    reason_codes: [notificationReason, "automation_justified=False"],
    automation_justified: false,
    verification_required: true,
    blocked: true,
    notification_reason: notificationReason,
  };
}

export async function verify(verifier: Verifier, signature: string): Promise<boolean> {
  if (!signature) {
    throw new Error("CIDF verification requires a non-empty signature.");
  }
  await verifier.refreshOnceIfNeeded();
  const text = await verifier.extractText();
  return text.includes(signature);
}

export async function executeWithFallback(
  decision: Decision,
  executors: Partial<Record<ToolName, (content: string) => Promise<void>>>,
  verifier: Verifier,
  content: string,
  signature: string,
): Promise<ExecutionResult> {
  if (!signature) {
    throw new Error("CIDF execution requires a non-empty signature.");
  }
  if (decision.blocked || !decision.chosen_tool) {
    return {
      status: "blocked",
      attempts: [],
      notification_reason:
        decision.notification_reason ||
        "no_eligible_method_and_automation_gate_closed",
    };
  }

  const chain: ToolName[] = [decision.chosen_tool, ...decision.fallback_chain];
  let attempts: AttemptLog[] = [];

  for (const tool of chain) {
    const executor = executors[tool];
    if (!executor) {
      attempts = [...attempts, { tool, result: "no_executor_registered" }];
      continue;
    }
    try {
      await executor(content);
    } catch (error) {
      attempts = [
        ...attempts,
        {
          tool,
          result: "execution_failed",
          detail: error instanceof Error ? error.name : "UnknownError",
        },
      ];
      continue;
    }
    try {
      const verified = await verify(verifier, signature);
      if (verified) {
        attempts = [...attempts, { tool, result: "success" }];
        return { status: "success", tool, attempts };
      }
    } catch (error) {
      attempts = [
        ...attempts,
        {
          tool,
          result: "verification_error",
          detail: error instanceof Error ? error.name : "UnknownError",
        },
      ];
      continue;
    }
    attempts = [...attempts, { tool, result: "verification_failed" }];
  }

  return {
    status: "failed",
    attempts,
    notification_reason: "all_eligible_methods_exhausted",
  };
}
