#!/usr/bin/env python3
"""run_h5_gpu_benchmark.py — H5 iterations-to-pass harness (Win 27B / LM Studio).

Runs 3 rubric-scored autoresearch-coder prompts with up to 5 iterations each.
Scores responses programmatically; on fail, feeds rubric feedback into the next turn.

Usage:
    python run_h5_gpu_benchmark.py
    python run_h5_gpu_benchmark.py --base-url http://localhost:1234/v1 --max-iterations 5
    python run_h5_gpu_benchmark.py --output references/results/gpu-results-h5.json
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

_SCRIPT_DIR = Path(__file__).resolve().parent
_DEFAULT_MODEL = "qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2"


@dataclass
class IterationResult:
    iteration: int
    wall_s: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    passed: bool
    rubric_notes: str
    content_chars: int


@dataclass
class TaskResult:
    task_id: str
    title: str
    iterations_to_pass: int | None
    total_wall_s: float
    total_tokens: int
    passed: bool
    iterations: list[IterationResult] = field(default_factory=list)


def _extract_text(msg: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("content", "reasoning_content", "reasoning"):
        val = msg.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val)
    return "\n".join(parts)


def _extract_code(text: str) -> str:
    blocks = re.findall(r"```(?:python)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if blocks:
        return max(blocks, key=len).strip()
    return text.strip()


def _chat(
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    timeout: int,
) -> tuple[str, dict[str, int], float]:
    root = base_url.rstrip("/").removesuffix("/v1")
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        root + "/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read())
    wall = time.perf_counter() - t0
    msg = body.get("choices", [{}])[0].get("message", {})
    usage = body.get("usage") or {}
    tokens = {
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
    }
    return _extract_text(msg), tokens, wall


def _score_clamp(text: str) -> tuple[bool, str]:
    code = _extract_code(text)
    try:
        ns: dict[str, Any] = {}
        exec(code, ns)  # noqa: S102 — rubric sandbox for generated snippet
    except Exception as exc:
        return False, f"compile/exec failed: {exc}"
    fn = ns.get("clamp")
    if not callable(fn):
        return False, "missing callable clamp(value, lo, hi)"
    cases = [(5, 0, 10, 5), (-1, 0, 10, 0), (11, 0, 10, 10), (3, 3, 3, 3)]
    for val, lo, hi, expected in cases:
        try:
            got = fn(val, lo, hi)
        except Exception as exc:
            return False, f"runtime error clamp({val},{lo},{hi}): {exc}"
        if got != expected:
            return False, f"clamp({val},{lo},{hi}) -> {got!r}, expected {expected!r}"
    return True, "clamp passes edge cases"


def _score_pytest(text: str) -> tuple[bool, str]:
    code = _extract_code(text)
    if "def test_" not in code:
        return False, "missing def test_*"
    if "assert" not in code:
        return False, "missing assert in test"
    if "pytest" not in code and "import pytest" not in code:
        # allow bare assert style
        pass
    try:
        ast.parse(code)
    except SyntaxError as exc:
        return False, f"syntax error: {exc}"
    if "add(" not in code and "add " not in code:
        return False, "test should target add(a, b) helper"
    return True, "pytest module parses; has test + assert for add"


def _score_refactor(text: str) -> tuple[bool, str]:
    code = _extract_code(text)
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, f"syntax error: {exc}"
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if not funcs:
        return False, "no function definitions found"
    names = {f.name for f in funcs}
    if not {"area_circle", "area_square"} <= names and not {"area_circle", "area_square"}.intersection(names):
        # accept renamed but require two area helpers + shared pi usage
        area_funcs = [f for f in funcs if f.name.startswith("area_")]
        if len(area_funcs) < 2:
            return False, "expected area_circle and area_square (or area_* pair)"
    joined = code.lower()
    if joined.count("3.14159") + joined.count("math.pi") + joined.count("pi *") < 2:
        return False, "refactor should reuse pi constant (DRY), not duplicate literal twice"
    if "def " in code and code.count("return") < 2:
        return False, "expected two area functions with returns"
    return True, "refactor shows shared pi / DRY structure"


@dataclass
class RubricTask:
    task_id: str
    title: str
    initial_prompt: str
    scorer: Callable[[str], tuple[bool, str]]
    fail_hint: str


TASKS: list[RubricTask] = [
    RubricTask(
        task_id="h5-clamp",
        title="Implement clamp(value, lo, hi)",
        initial_prompt=(
            "Write ONLY a Python function:\n\n"
            "def clamp(value, lo, hi):\n"
            "    \"\"\"Return value bounded to [lo, hi].\"\"\"\n\n"
            "No tests, no explanation — code block only."
        ),
        scorer=_score_clamp,
        fail_hint="Must compile, define clamp(value, lo, hi), and pass edge cases.",
    ),
    RubricTask(
        task_id="h5-pytest",
        title="Minimal pytest for add(a, b)",
        initial_prompt=(
            "Given:\n\n"
            "def add(a, b):\n"
            "    return a + b\n\n"
            "Write a minimal pytest file with at least one test function "
            "that asserts add() behavior. Code block only."
        ),
        scorer=_score_pytest,
        fail_hint="Need valid Python with def test_* and assert covering add().",
    ),
    RubricTask(
        task_id="h5-refactor",
        title="DRY refactor for area helpers",
        initial_prompt=(
            "Refactor this duplicated code to reuse pi (DRY). Return the full refactored module:\n\n"
            "import math\n\n"
            "def area_circle(r):\n"
            "    return 3.14159 * r * r\n\n"
            "def area_square(s):\n"
            "    return 3.14159 * s * s  # bug: should be s*s only; keep both functions\n\n"
            "Fix duplication; area_square should return s*s. Code block only."
        ),
        scorer=_score_refactor,
        fail_hint="Share pi via math.pi or constant; keep area_circle and area_square.",
    ),
]


def run_task(
    task: RubricTask,
    *,
    base_url: str,
    model: str,
    max_iterations: int,
    max_tokens: int,
    timeout: int,
) -> TaskResult:
    messages: list[dict[str, str]] = [{"role": "user", "content": task.initial_prompt}]
    iterations: list[IterationResult] = []
    total_wall = 0.0
    total_tokens = 0
    passed = False
    iterations_to_pass: int | None = None

    for i in range(1, max_iterations + 1):
        try:
            text, tok, wall = _chat(base_url, model, messages, max_tokens, timeout)
        except urllib.error.URLError as exc:
            ok, notes = False, f"request failed: {exc}"
            text = ""
            tok = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            wall = 0.0
        except Exception as exc:
            ok, notes = False, f"error: {exc}"
            text = ""
            tok = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            wall = 0.0
        else:
            ok, notes = task.scorer(text)

        total_wall += wall
        total_tokens += tok["total_tokens"]
        iterations.append(
            IterationResult(
                iteration=i,
                wall_s=round(wall, 2),
                prompt_tokens=tok["prompt_tokens"],
                completion_tokens=tok["completion_tokens"],
                total_tokens=tok["total_tokens"],
                passed=ok,
                rubric_notes=notes,
                content_chars=len(text),
            )
        )
        if ok:
            passed = True
            iterations_to_pass = i
            break
        feedback = (
            f"Rubric FAIL ({notes}). {task.fail_hint} "
            "Reply with corrected Python in a single fenced code block."
        )
        messages.append({"role": "assistant", "content": text or "(empty)"})
        messages.append({"role": "user", "content": feedback})

    return TaskResult(
        task_id=task.task_id,
        title=task.title,
        iterations_to_pass=iterations_to_pass,
        total_wall_s=round(total_wall, 2),
        total_tokens=total_tokens,
        passed=passed,
        iterations=iterations,
    )


def render_markdown(
    *,
    model: str,
    base_url: str,
    max_iterations: int,
    tasks: list[TaskResult],
    fanout_id: str,
) -> str:
    lines = [
        "# Win H5 GPU benchmark — iterations-to-pass",
        "",
        f"**Fan-out:** {fanout_id}",
        "**Author:** win-autoresearcher (Hermes)",
        "**Topic:** autoresearch/gpu-run",
        f"**Model:** `{model}` @ `{base_url}`",
        f"**Harness:** `run_h5_gpu_benchmark.py` (max {max_iterations} iterations/prompt)",
        "",
        "## Summary",
        "",
        "| Task | Pass | Iterations-to-pass | Total wall (s) | Total tokens |",
        "|------|------|--------------------|----------------|--------------|",
    ]
    for t in tasks:
        itp = str(t.iterations_to_pass) if t.iterations_to_pass is not None else f">{max_iterations - 1} (fail)"
        lines.append(
            f"| {t.task_id} | {'PASS' if t.passed else 'FAIL'} | {itp} | {t.total_wall_s} | {t.total_tokens} |"
        )
    lines.extend(["", "## Per-iteration detail", ""])
    for t in tasks:
        lines.append(f"### {t.task_id} — {t.title}")
        lines.append("")
        for it in t.iterations:
            lines.append(
                f"- iter {it.iteration}: {'PASS' if it.passed else 'FAIL'} — "
                f"{it.wall_s}s, {it.total_tokens} tok, {it.content_chars} chars — {it.rubric_notes}"
            )
        lines.append("")
    passed_n = sum(1 for t in tasks if t.passed)
    lines.extend(
        [
            "## H5 verdict (Win leg only)",
            "",
            f"- Tasks passed: **{passed_n}/3**",
            f"- Mac Ollama 9B leg: **pending** (compare iterations-to-pass + total wall)",
            "",
            "**Note:** Reasoning model may emit tokens in `reasoning_content`; harness scores extracted text/code.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="H5 GPU iterations-to-pass benchmark")
    p.add_argument("--base-url", default="http://localhost:1234/v1")
    p.add_argument("--model", default=_DEFAULT_MODEL)
    p.add_argument("--max-iterations", type=int, default=5)
    p.add_argument("--max-tokens", type=int, default=1024)
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--fanout-id", default="2026-06-28-coord-003")
    p.add_argument("--output-json", help="Write JSON results path")
    p.add_argument("--output-md", help="Write markdown results path")
    args = p.parse_args(argv)

    results: list[TaskResult] = []
    for task in TASKS:
        print(f"--- {task.task_id} ---", file=sys.stderr)
        results.append(
            run_task(
                task,
                base_url=args.base_url,
                model=args.model,
                max_iterations=args.max_iterations,
                max_tokens=args.max_tokens,
                timeout=args.timeout,
            )
        )

    payload = {
        "fanout_id": args.fanout_id,
        "model": args.model,
        "base_url": args.base_url,
        "max_iterations": args.max_iterations,
        "tasks": [asdict(r) for r in results],
    }
    md = render_markdown(
        model=args.model,
        base_url=args.base_url,
        max_iterations=args.max_iterations,
        tasks=results,
        fanout_id=args.fanout_id,
    )

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if args.output_md:
        Path(args.output_md).write_text(md, encoding="utf-8")

    print(md)
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
