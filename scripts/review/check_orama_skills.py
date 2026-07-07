#!/usr/bin/env python3
"""Validate orama-system SKILL.md files against the compact skill standard."""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_SCAN_ROOTS = (
    "bin/orama-system/skills",
    "bin/orama-system/afrp",
    "bin/orama-system/cidf",
    "bin/orama-system/gstack",
)
TARGET_NEW_SKILL_LINES = 200
HARD_SKILL_LINES = 500
CLAUDE_LISTING_CAP = 1536
HIGH_RISK_SKILLS = {"mcp-orchestration", "hermes-harness"}
SIDE_EFFECT_SKILLS = {"first-run-setup", "mcp-install", "openclaw-skills", "code-review", "git-history-surgery", "hermes-harness", "mcp-orchestration"}
BACKGROUND_SKILLS = {"afrp", "cidf"}
FORK_RECOMMENDED_SKILLS = {"code-review", "gstack", "hermes-harness", "mcp-orchestration"}
EFFORT_RECOMMENDATIONS = {"shell-hygiene": "low", "afrp": "low", "cidf": "low", "gstack": "medium", "openclaw-skills": "medium", "skillify": "high", "code-review": "high", "git-history-surgery": "high", "hermes-harness": "high", "mcp-orchestration": "high"}
VALID_EFFORTS = {"low", "medium", "high", "xhigh", "max"}
KNOWN_FIELDS = {
    "name", "description", "when_to_use", "argument-hint", "arguments",
    "disable-model-invocation", "user-invocable", "allowed-tools",
    "disallowed-tools", "model", "effort", "context", "agent", "hooks",
    "paths", "shell", "version", "license", "compatibility",
    "parent_skill", "triggers", "canonical_path", "supersedes",
    "last_updated", "agent_compatibility", "layer", "upstream",
    "upstream_path", "origin",
    # gstack-specific fields (legitimate for gstack-originated skills)
    "gstack_version", "gstack_install",
}

FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*\n", re.DOTALL)
FENCE_LINE_RE = re.compile(r"^```(?P<info>[^`]*)$", re.MULTILINE)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
RAW_LAN_IP_RE = re.compile(r"(?:10\.|172\.(?:1[6-9]|2\d|3[0-1])\.|192\.168\.)\d{1,3}\.\d{1,3}")


@dataclass(frozen=True)
class Finding:
    severity: str
    path: str
    rule: str
    message: str


def repo_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def parse_frontmatter(text: str) -> dict[str, object]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    fields: dict[str, object] = {}
    current_key: str | None = None
    list_key: str | None = None
    for raw_line in match.group("body").splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and list_key:
            fields.setdefault(list_key, [])
            assert isinstance(fields[list_key], list)
            fields[list_key].append(line[4:].strip().strip('"\''))
            continue
        key_match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if key_match:
            key, value = key_match.group(1), key_match.group(2).strip()
            current_key = key
            list_key = key if value == "" else None
            if value in {">-", "|", "|-"}:
                fields[key] = ""
            elif value == "":
                fields[key] = []
            else:
                fields[key] = value.strip('"\'')
            continue
        if current_key and raw_line.startswith("  ") and isinstance(fields.get(current_key), str):
            fields[current_key] = f"{fields[current_key]} {line.strip()}".strip()
    return fields


def field_bool(value: object) -> bool | None:
    lowered = str(value).strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return None


def iter_skill_files(root: Path, scan_roots: Iterable[str]) -> list[Path]:
    found: set[Path] = set()
    for rel in scan_roots:
        base = root / rel
        if base.is_file() and base.name == "SKILL.md":
            found.add(base)
        elif base.is_dir():
            found.update(base.rglob("SKILL.md"))
    return sorted(found)


def infer_skill_name(path: Path) -> str:
    return path.parent.name


def iter_opening_fences(text: str) -> Iterable[tuple[int, str]]:
    in_fence = False
    for line_no, line in enumerate(text.splitlines(), 1):
        match = FENCE_LINE_RE.match(line)
        if not match:
            continue
        info = match.group("info").strip()
        if not in_fence:
            yield line_no, info
            in_fence = True
        else:
            in_fence = False


def leading_parent_segments(target: str) -> int:
    count = 0
    while target.startswith("../"):
        count += 1
        target = target[3:]
    return count


def parse_warning_allowlist(entries: Iterable[str]) -> set[tuple[str, str | None]]:
    allowed: set[tuple[str, str | None]] = set()
    for entry in entries:
        cleaned = entry.strip()
        if not cleaned or cleaned.startswith("#"):
            continue
        if ":" in cleaned:
            rule, path = cleaned.split(":", 1)
            allowed.add((rule.strip(), path.strip() or None))
        else:
            allowed.add((cleaned, None))
    return allowed


def warning_is_allowed(finding: Finding, allowlist: set[tuple[str, str | None]]) -> bool:
    return (finding.rule, None) in allowlist or (finding.rule, finding.path) in allowlist


def has_personal_path(text: str) -> bool:
    return any(token in text for token in ("/Users/", "/home/", "C:/Users/", "C:\\Users\\"))


def validate_skill(path: Path, repo_root: Path, strict: bool) -> list[Finding]:
    rel = repo_relative(path, repo_root)
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    findings: list[Finding] = []

    def add(severity: str, rule: str, message: str) -> None:
        findings.append(Finding(severity, rel, rule, message))

    skill_name = str(fm.get("name", ""))
    directory_name = infer_skill_name(path)
    effective_name = skill_name or directory_name
    description = str(fm.get("description", ""))
    when_to_use = str(fm.get("when_to_use", ""))
    listing = " ".join(part for part in (description, when_to_use) if part)

    if not fm:
        add("error", "frontmatter", "missing YAML frontmatter")
    if not skill_name:
        add("error", "frontmatter.name", "missing name")
    elif not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", skill_name):
        add("error", "frontmatter.name", f"invalid name: {skill_name!r}")
    elif skill_name != directory_name and directory_name not in {"afrp", "cidf", "gstack"}:
        add("warn", "frontmatter.name", f"name {skill_name!r} does not match directory {directory_name!r}")
    for field in sorted(set(fm) - KNOWN_FIELDS):
        add("warn", "frontmatter.unknown-field", f"unrecognized frontmatter field {field!r}")
    if not description:
        add("error", "frontmatter.description", "missing description")
    if not any(token in f"{description} {when_to_use}".lower() for token in ("use when", "activates", "trigger", "use for", "when the user")):
        add("warn", "frontmatter.when_to_use", "description/when_to_use should include activation contexts")
    if len(listing) > CLAUDE_LISTING_CAP:
        add("error" if strict else "warn", "frontmatter.listing-cap", f"description + when_to_use is {len(listing)} chars; max {CLAUDE_LISTING_CAP}")
    if len(description) > 600 and not when_to_use:
        add("warn", "frontmatter.when_to_use", "long description should move triggers into when_to_use")

    effort = str(fm.get("effort", "")).strip().lower()
    if effort and effort not in VALID_EFFORTS:
        add("error", "frontmatter.effort", f"invalid effort {effort!r}")
    if EFFORT_RECOMMENDATIONS.get(effective_name) and not effort:
        add("warn", "frontmatter.effort", f"consider effort: {EFFORT_RECOMMENDATIONS[effective_name]}")
    if effective_name in SIDE_EFFECT_SKILLS and field_bool(fm.get("disable-model-invocation")) is not True:
        add("error" if strict else "warn", "frontmatter.disable-model-invocation", "side-effect skill should require explicit user invocation")
    if effective_name in BACKGROUND_SKILLS and field_bool(fm.get("user-invocable")) is not False:
        add("error" if strict else "warn", "frontmatter.user-invocable", "background doctrine skill should not appear as a user command")
    if effective_name in FORK_RECOMMENDED_SKILLS and str(fm.get("context", "")).strip().lower() != "fork":
        add("warn", "frontmatter.context", "review/QA/harness skill should consider context: fork")
    if str(fm.get("context", "")).strip().lower() == "fork" and not fm.get("agent"):
        add("warn", "frontmatter.agent", "context: fork should usually name an agent")

    line_count = len(text.splitlines())
    if line_count > HARD_SKILL_LINES:
        add("error" if strict else "warn", "size.hard-ceiling", f"SKILL.md has {line_count} lines")
    elif line_count > TARGET_NEW_SKILL_LINES:
        add("warn", "size.target", f"SKILL.md has {line_count} lines")
    for line_no, fence_info in iter_opening_fences(text):
        if not fence_info:
            add("error", "markdown.code-fence", f"opening code fence at line {line_no} has no language specifier")
    if has_personal_path(text):
        add("error", "opsec.personal-path", "contains an absolute workstation path")
    if RAW_LAN_IP_RE.search(text):
        add("warn", "opsec.raw-lan-ip", "contains raw LAN IP; prefer env placeholders")
    if ".claude/skills/" in text and "never `.claude/skills/`" not in text.lower():
        add("warn", "path.canonical-root", "mentions .claude/skills; ensure it is not canonical")
    if "scripts/" in text and "${CLAUDE_SKILL_DIR}" not in text and "${CLAUDE_PROJECT_DIR}" not in text:
        add("warn", "portability.skill-dir", "script references should prefer portable project/skill env vars")
    if "hooks:" in text and "${CLAUDE_SESSION_ID}" not in text:
        add("warn", "audit.session-id", "hooked audit flows should include session id")
    link_depth_warnings = 0
    for target in LINK_RE.findall(text):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        if leading_parent_segments(target) > 1 and link_depth_warnings < 3:
            add("warn", "references.one-level", f"reference link is deeper than one parent: {target}")
            link_depth_warnings += 1
    lower = text.lower()
    if "when to use" not in lower and not when_to_use:
        add("warn", "usability.when-to-use", "missing explicit When To Use section or metadata")
    if "when not" not in lower and "do not use" not in lower:
        add("warn", "usability.when-not-to-use", "missing when-not-to-use guidance")
    if effective_name in HIGH_RISK_SKILLS:
        for label, tokens in {"HITL/Gate": ("hitl", "human-in-the-loop", "human approval", "human-approval"), "audit": ("audit", "audit_log", "jsonl"), "context firewall": ("context-firewall", "firewall", "mediator")}.items():
            if not any(token in lower for token in tokens):
                add("error" if strict else "warn", "high-risk.precondition", f"high-risk skill missing {label}")
    if "jargon" not in lower and "glossary" not in lower:
        add("warn", "distillation.jargon", "define jargon once")
    if "imperative" not in lower and "runbook" not in lower:
        add("warn", "distillation.voice", "use imperative runbook voice")
    return findings


def load_allowlist(path: str | None) -> list[str]:
    if not path:
        return []
    allowlist_path = Path(path)
    if not allowlist_path.exists():
        raise FileNotFoundError(f"warning allowlist file not found: {path}")
    return allowlist_path.read_text(encoding="utf-8").splitlines()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="repository root")
    parser.add_argument("--mode", choices=("baseline", "strict"), default="baseline")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--scan-root", dest="scan_roots", action="append", help="skill scan root relative to repository root; can repeat")
    parser.add_argument("--allow-warning", dest="allow_warnings", action="append", default=[], help="allow warning by rule or path in strict mode")
    parser.add_argument("--warning-allowlist", help="file containing allowed warning rules, one per line")
    args = parser.parse_args(argv)

    repo_root = Path(args.root).resolve()
    scan_roots = tuple(args.scan_roots) if args.scan_roots else DEFAULT_SCAN_ROOTS
    allowlist = parse_warning_allowlist([*load_allowlist(args.warning_allowlist), *args.allow_warnings])
    findings: list[Finding] = []
    for path in iter_skill_files(repo_root, scan_roots):
        findings.extend(validate_skill(path, repo_root, strict=args.mode == "strict"))
    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warn"]
    unallowed_warnings = [f for f in warnings if not warning_is_allowed(f, allowlist)]
    payload = {"mode": args.mode, "error_count": len(errors), "warning_count": len(warnings), "unallowed_warning_count": len(unallowed_warnings), "findings": [asdict(f) for f in findings]}
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"ORAMA_SKILL_CHECK mode={args.mode} errors={len(errors)} warnings={len(warnings)} unallowed_warnings={len(unallowed_warnings)}")
        for finding in findings:
            allowed = " allowed" if finding.severity == "warn" and warning_is_allowed(finding, allowlist) else ""
            print(f"{finding.severity.upper()}{allowed} {finding.path} [{finding.rule}] {finding.message}")
    return 1 if args.mode == "strict" and (errors or unallowed_warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))