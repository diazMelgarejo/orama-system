"""
content_insertion_framework.py
──────────────────────────────
Platform-agnostic core library for the Content Insertion Decision Framework v1.3.
All other Python-based integrations (LangChain, CrewAI) import from here.

No external dependencies required.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Protocol


# ─── Data models ──────────────────────────────────────────────────────────────

@dataclass
class Task:
    """Describes what needs to be done."""
    task_type: str
    is_one_time: bool
    frequency_estimate: int
    content_static: bool
    requires_transformation: bool
    requires_conditional_logic: bool
    requires_external_integration: bool
    content_length_chars: int
    format_requirements: str
    signature: str
    estimated_setup_seconds: Optional[float] = None
    estimated_run_seconds: Optional[float] = None


@dataclass
class Env:
    """Describes what methods are available in the current environment."""
    field_accessible: bool
    editor_visible: bool
    paste_supported: bool
    upload_available: bool
    max_safe_chars_form_input: int = 10_000
    max_safe_chars_typing: int = 5_000
    formatting_preserved_on_paste: bool = True


@dataclass
class Decision:
    """Output of decide(). A blocked decision means notify the user; do not execute."""
    chosen_tool: Optional[str]
    fallback_chain: List[str]
    reason_codes: List[str]
    automation_justified: bool
    verification_required: bool = True
    blocked: bool = False
    notification_reason: Optional[str] = None


@dataclass
class AttemptLog:
    tool: str
    result: str
    detail: str = ""


@dataclass
class ExecutionResult:
    status: str
    tool: Optional[str] = None
    attempts: List[AttemptLog] = field(default_factory=list)
    notification_reason: Optional[str] = None


# ─── Core logic ───────────────────────────────────────────────────────────────

def automation_justified(task: Task) -> bool:
    """
    Return whether scripting may be considered after ranks 1–4 are exhausted.

    The gate fails closed for one-time static work and when known setup time
    exceeds one execution. Otherwise, any repeat/logic/transformation/external
    integration signal justifies considering scripting as the final fallback.
    """
    if task.is_one_time and task.content_static:
        return False
    if (
        task.estimated_setup_seconds is not None
        and task.estimated_run_seconds is not None
        and task.estimated_setup_seconds > task.estimated_run_seconds
    ):
        return False
    return (
        task.frequency_estimate >= 5
        or task.requires_conditional_logic
        or task.requires_transformation
        or task.requires_external_integration
    )


def decide(task: Task, env: Env) -> Decision:
    """
    Select the lowest-complexity eligible method.

    Scripting never displaces ranks 1–4. It is appended only as a last-resort
    fallback when the automation gate is open. If no method is eligible and the
    gate is closed, return an explicit blocked decision so the caller can notify
    the user instead of inventing an unavailable tool.
    """
    reasons: List[str] = []
    tools: List[str] = []

    if env.field_accessible and task.content_length_chars <= env.max_safe_chars_form_input:
        tools.append("direct_form_input")
    if env.editor_visible and task.content_length_chars <= env.max_safe_chars_typing:
        tools.append("direct_typing")
    if env.paste_supported:
        tools.append("clipboard_paste")
    if env.upload_available:
        tools.append("file_upload")

    justified = automation_justified(task)
    if tools:
        if justified:
            tools.append("scripting")
            reasons.append("scripting_deferred_until_lower_ranks_exhausted")
        chosen = tools[0]
        fallback = tools[1:]
        reasons.append(f"chosen_{chosen}")
        reasons.append(f"automation_justified={justified}")
        return Decision(
            chosen_tool=chosen,
            fallback_chain=fallback,
            reason_codes=reasons,
            automation_justified=justified,
        )

    if justified:
        reasons.extend(["chosen_scripting", "automation_justified=True"])
        return Decision(
            chosen_tool="scripting",
            fallback_chain=[],
            reason_codes=reasons,
            automation_justified=True,
        )

    notification_reason = "no_eligible_method_and_automation_gate_closed"
    reasons.extend([notification_reason, "automation_justified=False"])
    return Decision(
        chosen_tool=None,
        fallback_chain=[],
        reason_codes=reasons,
        automation_justified=False,
        blocked=True,
        notification_reason=notification_reason,
    )


# ─── Verification ─────────────────────────────────────────────────────────────

class Verifier(Protocol):
    """
    Implement this per environment (web/DOM, desktop, API).
    Never use visual confirmation as a substitute.
    """
    def refresh_once_if_needed(self) -> None: ...
    def extract_text(self) -> str: ...


def verify(verifier: Verifier, signature: str) -> bool:
    """
    Programmatic ground truth. Returns True only when a non-empty signature
    is confirmed present in the extracted text.
    """
    if not signature:
        raise ValueError("CIDF verification requires a non-empty signature.")
    verifier.refresh_once_if_needed()
    return signature in verifier.extract_text()


# ─── Execution loop ───────────────────────────────────────────────────────────

def execute_with_fallback(
    decision: Decision,
    executors: Dict[str, Callable[[str], None]],
    verifier: Verifier,
    content: str,
    signature: str,
) -> ExecutionResult:
    """
    Execute the chosen method, then each fallback in order.

    Every execution, verification, and registration outcome is logged. Executor
    or verifier errors move to the next eligible fallback; they never abort the
    chain or create a false success.
    """
    if not signature:
        raise ValueError("CIDF execution requires a non-empty signature.")

    if decision.blocked or decision.chosen_tool is None:
        return ExecutionResult(
            status="blocked",
            notification_reason=(
                decision.notification_reason
                or "no_eligible_method_and_automation_gate_closed"
            ),
        )

    chain = [decision.chosen_tool] + decision.fallback_chain
    attempts: List[AttemptLog] = []

    for tool in chain:
        executor = executors.get(tool)
        if executor is None:
            attempts.append(AttemptLog(tool=tool, result="no_executor_registered"))
            continue
        try:
            executor(content)
        except Exception as error:
            attempts.append(
                AttemptLog(
                    tool=tool,
                    result="execution_failed",
                    detail=type(error).__name__,
                )
            )
            continue
        try:
            verified = verify(verifier, signature)
        except Exception as error:
            attempts.append(
                AttemptLog(
                    tool=tool,
                    result="verification_error",
                    detail=type(error).__name__,
                )
            )
            continue
        if verified:
            attempts.append(AttemptLog(tool=tool, result="success"))
            return ExecutionResult(status="success", tool=tool, attempts=attempts)
        attempts.append(AttemptLog(tool=tool, result="verification_failed"))

    return ExecutionResult(
        status="failed",
        attempts=attempts,
        notification_reason="all_eligible_methods_exhausted",
    )
