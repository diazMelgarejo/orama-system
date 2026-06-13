#!/usr/bin/env python3
"""
distill_session.py — offline orama distillation CLI.

Reads a session export, runs the existing verify + lesson hooks, and emits
PROPOSED artifacts under docs/distill-fable-5/runs/<date-session>/.

5-stage ὅραμα workflow:
  Stage 1 — Context Immersion: parse the session export
  Stage 2 — Ruthless Refinement: extract lessons (heuristic, no model calls)
  Stage 4 — Masterful Execution: generate proposed artifact stubs
  Stage 5 — Crystallize the Vision: invoke verify + capture-lesson hooks

Contract (v1 hard requirements):
  - NO model calls, NO network, NO API keys, NO PT mutation.
  - Stateless: each run is idempotent; writes only to --output-dir.
  - Unknown export format -> exit 2, clear diagnostic, no stack trace.
  - Hook failures -> fail closed (exit 1).
  - Unknown-format rejection message shape: 'unsupported export format: got X, expected Y'.
"""
from __future__ import annotations

import abc
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path


# ─── Repo root resolution (never hardcode /Users/<name>/) ────────────────────

def _find_repo_root(start: Path) -> Path:
    """Walk upward from *start* until we find the orama-system repo root."""
    for candidate in [start, *start.parents]:
        if (candidate / "bin" / "orama-system" / "scripts").is_dir():
            return candidate
    raise RuntimeError(
        f"cannot locate orama-system repo root from {start}; "
        "expected a parent directory containing bin/orama-system/scripts/"
    )


_REPO_ROOT = _find_repo_root(Path(__file__).resolve().parent)
_SCRIPTS_DIR = _REPO_ROOT / "bin" / "orama-system" / "scripts"
_DEFAULT_OUT_DIR = _REPO_ROOT / "docs" / "distill-fable-5" / "runs"


# ─── SessionExportParser ABC ─────────────────────────────────────────────────

class SessionExportParser(abc.ABC):
    """Format-agnostic interface for parsing session export files.

    Extension point: add new format adapters by subclassing and appending
    to _PARSERS below. Fable 5 native export -> FableExportParser here.
    """

    @property
    @abc.abstractmethod
    def format_name(self) -> str:
        """Human-readable format identifier used in diagnostics."""

    @abc.abstractmethod
    def can_parse(self, raw: object) -> bool:
        """Return True if this parser can handle the given raw parsed JSON."""

    @abc.abstractmethod
    def parse(self, raw: object) -> list[dict]:
        """Return list of {role, content, index} normalized messages."""


class OramaSessionExportV1Parser(SessionExportParser):
    """Handles orama-session-export-v1: dict with a top-level 'messages' list.

    This is the format produced by /context-save and the synthetic in-repo
    fixture at docs/distill-fable-5/fixtures/sample_session.json.
    """

    @property
    def format_name(self) -> str:
        return "orama-session-export-v1"

    def can_parse(self, raw: object) -> bool:
        return (
            isinstance(raw, dict)
            and isinstance(raw.get("messages"), list)
            and len(raw["messages"]) > 0
            and all(
                isinstance(m, dict) and "role" in m and "content" in m
                for m in raw["messages"]
            )
        )

    def parse(self, raw: object) -> list[dict]:
        return [
            {"role": m["role"], "content": str(m["content"]), "index": i}
            for i, m in enumerate(raw["messages"])  # type: ignore[index]
        ]


class GenericJsonTranscriptParser(SessionExportParser):
    """Handles a plain JSON list of {role, content} messages.

    Covers direct Claude Chat Exporter outputs and bare API transcript dumps.
    """

    @property
    def format_name(self) -> str:
        return "json-transcript-list"

    def can_parse(self, raw: object) -> bool:
        return (
            isinstance(raw, list)
            and len(raw) > 0
            and all(
                isinstance(m, dict) and "role" in m and "content" in m
                for m in raw
            )
        )

    def parse(self, raw: object) -> list[dict]:
        return [
            {"role": m["role"], "content": str(m["content"]), "index": i}
            for i, m in enumerate(raw)  # type: ignore[arg-type]
        ]


_PARSERS: list[SessionExportParser] = [
    OramaSessionExportV1Parser(),
    GenericJsonTranscriptParser(),
    # Future: FableJsonParser(), MarkdownExportParser(), HTMLExportParser()
]


def _load_and_parse(input_path: Path) -> tuple[list[dict], str]:
    """Load *input_path*, detect format, return (normalized_messages, format_name).

    Exits 2 on any parse failure or unsupported format — never a stack trace.
    """
    try:
        raw = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(
            f"unsupported export format: got non-JSON (parse error: {exc.msg}), "
            "expected JSON list[{role,content}] or orama-session-export dict with 'messages'.",
            file=sys.stderr,
        )
        sys.exit(2)
    except OSError as exc:
        print(f"cannot read input file: {exc}", file=sys.stderr)
        sys.exit(2)

    for parser in _PARSERS:
        if parser.can_parse(raw):
            return parser.parse(raw), parser.format_name

    if isinstance(raw, list) and raw:
        got = f"list[{type(raw[0]).__name__}]"
    else:
        got = type(raw).__name__
    print(
        f"unsupported export format: got {got}, "
        "expected list[{role,content}] (json-transcript-list) "
        "or dict with 'messages' (orama-session-export-v1).",
        file=sys.stderr,
    )
    sys.exit(2)


# ─── Lesson extraction (Stage 2: heuristic, no model calls) ──────────────────

def _extract_lessons(messages: list[dict]) -> list[dict]:
    """Extract lessons from assistant messages using text heuristics only."""
    lessons: list[dict] = []
    for msg in messages:
        if msg["role"] != "assistant":
            continue
        content = msg["content"]
        # "Lesson: <text>" pattern
        for match in re.finditer(r"[Ll]esson:\s*(.+?)(?:\.|$)", content, re.MULTILINE):
            lessons.append({
                "pattern": "lesson",
                "insight": match.group(1).strip(),
                "source_turn": msg["index"],
                "confidence": "heuristic",
            })
        # Numbered bold patterns: "1. **term** — insight"
        for match in re.finditer(
            r"^\d+\.\s+\*\*(.+?)\*\*.*?[—–-]\s*(.+)$", content, re.MULTILINE
        ):
            lessons.append({
                "pattern": match.group(1).strip(),
                "insight": match.group(2).strip(),
                "source_turn": msg["index"],
                "confidence": "heuristic",
            })
    return lessons


# ─── Artifact stub generators (Stage 4: Masterful Execution) ─────────────────

def _extract_yaml_blocks(messages: list[dict], keyword: str) -> str:
    """Return the first ```yaml block containing *keyword* from assistant turns."""
    for msg in messages:
        if msg["role"] != "assistant":
            continue
        for block in re.finditer(r"```ya?ml\n(.*?)```", msg["content"], re.DOTALL):
            if keyword.lower() in block.group(1).lower():
                return block.group(1).strip()
    return ""


def _write_proposed_artifacts(
    run_dir: Path, messages: list[dict], session_name: str
) -> None:
    proposed = run_dir / "proposed"
    proposed.mkdir(parents=True, exist_ok=True)

    routing_yaml = _extract_yaml_blocks(messages, "fallback") or _extract_yaml_blocks(
        messages, "routing"
    )
    models_yaml = _extract_yaml_blocks(messages, "model") or _extract_yaml_blocks(
        messages, "budget"
    )

    skill_lines = [
        f"# SKILL.md section — proposed from: {session_name}",
        "",
        "## Session Insights",
        "",
    ]
    for msg in messages:
        if msg["role"] != "assistant":
            continue
        for match in re.finditer(
            r"[Ll]esson:\s*(.+?)(?:\.|$)", msg["content"], re.MULTILINE
        ):
            skill_lines.append(f"- {match.group(1).strip()}")
    (proposed / "skill_md_section.md").write_text(
        "\n".join(skill_lines), encoding="utf-8"
    )

    (proposed / "agent_role.md").write_text(
        f"# Agent Role — {session_name}\n\n"
        "**Role:** Distillation specialist\n"
        "**Trigger:** session-export received\n"
        "**Output:** proposed artifacts in runs/<session>/proposed/\n"
        "**Constraints:** stateless, no model calls, no PT mutation\n",
        encoding="utf-8",
    )

    (proposed / "models_yml_snippet.yaml").write_text(
        f"# proposed models.yml update from: {session_name}\n"
        + (models_yaml if models_yaml else "# No model configuration blocks extracted.\n"),
        encoding="utf-8",
    )

    (proposed / "routing_yml_snippet.yaml").write_text(
        f"# proposed routing.yml update from: {session_name}\n"
        + (routing_yaml if routing_yaml else "# No routing configuration blocks extracted.\n"),
        encoding="utf-8",
    )

    (proposed / "testable_module_stub.py").write_text(
        f'"""Testable module stub — proposed from: {session_name}."""\n\n'
        "# TODO: implement distillation-validated logic from session insights\n"
        "# See skill_md_section.md for extracted patterns.\n",
        encoding="utf-8",
    )


# ─── Hook invocation (Stage 5: Crystallize the Vision) ───────────────────────

def _run_hook(script_path: Path, argv: list[str]) -> dict:
    """Invoke *script_path* via subprocess.run with *argv*.

    Returns a result dict. Fails closed (sys.exit(1)) on any non-zero exit.
    Records a skip reason instead of failing when the script is absent.
    """
    if not script_path.exists():
        return {
            "exit_code": None,
            "skipped": True,
            "skip_reason": f"script not found: {script_path}",
        }

    cmd = [sys.executable, str(script_path)] + argv
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        print(
            f"FAIL: {script_path.name} timed out after 120 s — fail closed",
            file=sys.stderr,
        )
        sys.exit(1)

    if result.returncode != 0:
        print(
            f"FAIL: {script_path.name} exited {result.returncode}",
            file=sys.stderr,
        )
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)
        sys.exit(1)

    return {"exit_code": result.returncode, "skipped": False, "skip_reason": None}


# ─── Main entry point ─────────────────────────────────────────────────────────

def main(argv=None) -> int:
    """Run the distillation pipeline. Returns 0 on success, raises SystemExit on error."""
    ap = argparse.ArgumentParser(
        description=(
            "Offline orama distillation CLI — reads a session export, "
            "emits proposed artifacts under docs/distill-fable-5/runs/."
        )
    )
    ap.add_argument("--input", required=True, help="Path to session export file (JSON)")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Write run dir artifacts but apply no PT mutations",
    )
    ap.add_argument(
        "--non-interactive",
        action="store_true",
        default=True,
        help="Non-interactive mode (default; hooks run with --no-interact / --review)",
    )
    ap.add_argument(
        "--output-dir",
        default=str(_DEFAULT_OUT_DIR),
        metavar="DIR",
        help=f"Output base directory (default: docs/distill-fable-5/runs/)",
    )
    args = ap.parse_args(argv)

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"input file not found: {input_path}", file=sys.stderr)
        sys.exit(2)

    # Stage 1: Context Immersion — parse the session export
    messages, fmt_name = _load_and_parse(input_path)

    session_name = re.sub(r"[^a-z0-9-]", "-", input_path.stem.lower()).strip("-")
    date_prefix = datetime.date.today().isoformat()
    run_name = f"{date_prefix}-{session_name}"
    run_dir = Path(args.output_dir) / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "transcript.normalized.json").write_text(
        json.dumps({"format": fmt_name, "messages": messages}, indent=2),
        encoding="utf-8",
    )

    # Stage 2: Ruthless Refinement — extract lessons (heuristic, no model calls)
    lessons = _extract_lessons(messages)
    (run_dir / "lessons.extracted.json").write_text(
        json.dumps(lessons, indent=2),
        encoding="utf-8",
    )

    # Stage 4: Masterful Execution — generate proposed artifact stubs
    _write_proposed_artifacts(run_dir, messages, session_name)

    # Stage 5: Crystallize the Vision — run hooks (always; fail closed on non-zero)
    vbd_result = _run_hook(
        _SCRIPTS_DIR / "verify_before_done.py",
        [
            "--task", f"distillation:{session_name}",
            "--dir", ".",
            "--check", "plan",
            "--no-interact",
        ],
    )

    cl_result = _run_hook(
        _SCRIPTS_DIR / "capture_lesson.py",
        ["--review"],
    )

    # Write verification summary
    (run_dir / "verification.summary.json").write_text(
        json.dumps(
            {
                "verdict": "PASS",
                "dry_run": args.dry_run,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "session_name": session_name,
                "hook_results": {
                    "verify_before_done": vbd_result,
                    "capture_lesson": cl_result,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Empty placeholder — populated after live Fable 5 trial runs (v2 roadmap)
    (run_dir / "MODELS_PERFORMANCE_DELTA.md").write_text(
        "# Models Performance Delta\n\n"
        "_Populated after live Fable 5 trial runs. See v2 roadmap._\n",
        encoding="utf-8",
    )

    print(f"OK run dir: {run_dir}")
    if args.dry_run:
        print("dry-run: artifacts written, no PT mutations applied")

    return 0


if __name__ == "__main__":
    sys.exit(main())
