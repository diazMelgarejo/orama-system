#!/usr/bin/env python3
"""PreToolUse guard for the Bash tool: stop commands that are fine in bash on Linux but fail or
misbehave under zsh and the BSD tools on macOS, or that dump secrets, before they run.

Every rule is data (id, level, summary, fix hint) with bad and good fixtures. `--self-test` runs the
fixtures, `--markdown` renders the rule table that shell-hygiene/SKILL.md embeds (a test keeps the
two equal), and the same registry drives the hook, so the rules, the docs and the tests cannot drift.

Hook protocol (Claude Code PreToolUse): JSON on stdin; exit 2 blocks and feeds stderr back to the
model; exit 0 with a JSON `additionalContext` warns without blocking.

Controls:
  # gotcha-ok: <id>[,<id>] (or `all`)   in the command: skip those rules for that command
  SHELL_GOTCHAS_MODE=enforce|warn|off   enforce (default) blocks; warn downgrades every block to a
                                        warning (staged rollout); off disables the hook
  --report                              show how often each rule fired (from the log)
  SHELL_GOTCHAS_LOG=<file>              usage log (rule ids and a command hash only, never the
                                        command text); default $XDG_STATE_HOME/shell-gotchas/usage.log,
                                        else the same path under ~/.local/state; never written inside
                                        the Claude configuration directory
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import shlex
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Callable

STMT = r"(?:^|[;&|(\n]|\bthen\b|\bdo\b|\belse\b)[ \t]*"
HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)(\w+)\1[^\n]*\n.*?^[ \t]*\2[ \t]*$", re.S | re.M)
BASH_BODY = re.compile(r"(?:^|[\s;&|(])(?:\S*/)?bash(?:[ \t]+-[A-Za-z]+)*[ \t]*(?:-c\b|-s\b|<<|<\()|^#!.*\bbash\b", re.M)
ESCAPE = re.compile(r"#[ \t]*gotcha-ok[ \t]*:[ \t]*([\w,*-]+)")
CREATES_FILES = re.compile(r"\b(?:touch|mkdir|cp|mv|tar|unzip|gunzip|make|cmake|npm|pnpm|yarn|pip3?|python3?|node|cargo|go|curl|wget|git[ \t]+(?:checkout|pull|clone|restore|reset|stash|merge|rebase))\b|>")
NO_WORDS = {"echo", "printf", "test", "[", "[[", "cd", "export", "read", "unset", "return", "local"}
RESERVED = "status|pipestatus|path|argv|options|commands|aliases|functions|nameddirs"
LIST_PRODUCERS = r"(?:ls|find|fd|rg|grep|git[ \t]+(?:ls-files|diff|status|log|branch|tag)|sort|uniq|cut|tr|awk|sed|cat|head|tail)"
COMMAND_WORDS = r"(?:git|gh|python3?|node|npm|pnpm|pytest|curl|codex|ls|grep|rg|sed|awk|find|docker|make)"


@dataclass(frozen=True)
class Rule:
    """One guarded shell gotcha: what it is, how to fix it, and fixtures that prove it."""

    id: str
    level: str  # "deny" blocks the command, "warn" adds context without blocking
    summary: str
    hint: str
    check: Callable[[str, str], bool]  # (heredoc-stripped command, cwd) -> fires?
    bad: tuple[str, ...]
    good: tuple[str, ...]
    zsh_only: bool = False  # skipped when the command's body runs under bash


def pat(pattern: str) -> Callable[[str, str], bool]:
    """Return a check that fires when *pattern* matches anywhere in the command."""
    regex = re.compile(pattern, re.M)
    return lambda command, _cwd: bool(regex.search(command))


def _after_cmdsub(command: str, start: int) -> int:
    """Return the index just past the `$( ... )` that opens at or after *start*."""
    i, depth = command.index("$(", start) + 2, 1
    while i < len(command) and depth:
        depth += (command[i] == "(") - (command[i] == ")")
        i += 1
    return i


def _unquoted_list_var(command: str, _cwd: str) -> bool:
    """A multi-word `$(...)` result stored in a variable and then used unquoted as arguments."""
    for m in re.finditer(r"(?<![\w$])([A-Za-z_]\w*)=\"?\$\([ \t]*" + LIST_PRODUCERS + r"\b", command):
        name, end = m.group(1), _after_cmdsub(command, m.start())
        for stmt in re.split(r"[;&|\n]+", command[end:]):
            words = stmt.split()
            if words and words[0] not in NO_WORDS and re.search(r"(?<![\"'\w$])\$\{?" + name + r"\}?(?=\s|$)", stmt):
                return True
    return False


def _command_in_variable(command: str, _cwd: str) -> bool:
    """A command line stored in a string variable and then run as `$VAR args`."""
    pattern = r"""(?<![\w$])([A-Za-z_]\w*)=(["'])""" + COMMAND_WORDS + r"""\b[^"']*\2"""
    return any(re.search(STMT + r"\$\{?" + m.group(1) + r"\}?[ \t]", command) for m in re.finditer(pattern, command))


def _unmatched_glob(command: str, cwd: str) -> bool:
    """An unquoted glob that matches nothing in the working directory aborts the whole zsh command."""
    if re.search(r"\b(?:cd|pushd|ssh|docker|kubectl)\b|nonomatch|setopt|\(N\)|nullglob", command):
        return False
    for stmt in re.split(r"[;&|\n]+", command):
        if CREATES_FILES.search(stmt):
            return False  # later globs may match files this command is about to create
        if not stmt.strip() or stmt.lstrip().startswith(("case ", "[[", "[ ", "if [", "for ", "while ")):
            continue
        try:
            tokens = shlex.split(stmt, posix=False)
        except ValueError:
            continue
        for tok in tokens[1:]:
            if tok in ("[", "[[") or tok.startswith("-") or re.search(r"[\"'`$\\{]", tok):
                continue
            if re.fullmatch(r"[A-Za-z0-9_./~*?\[\]-]+", tok) and re.search(r"[*?\[]", tok):
                path = os.path.expanduser(tok) if tok.startswith("~") else os.path.join(cwd, tok)
                if not glob.glob(path):
                    return True
    return False


def _env_dump(command: str, _cwd: str) -> bool:
    """`env`, `printenv` or `export -p` with no filter that drops the values."""
    start = STMT + r"(?:env|printenv|export[ \t]+-p|declare[ \t]+-x|typeset[ \t]+-x)[ \t]*(?=\||;|&&|$)"
    safe = r"\|[ \t]*(?:cut[ \t]+-d[ \t]*=[ \t]*-f[ \t]*1|wc\b|grep[ \t]+-\w*[cq]\w*)"
    return any(not re.search(safe, command[m.end():].split("\n")[0]) for m in re.finditer(start, command, re.M))


def _commit_without_message(command: str, _cwd: str) -> bool:
    """`git commit` that would open an editor: no message flag in its arguments."""
    flags = r"(?:^|[ \t])(?:-[A-Za-z]*[mFCc][A-Za-z]*(?:[ \t=]|$)|--message|--file|--no-edit|--allow-empty-message|--reuse-message)"
    return any(
        not re.search(flags, m.group(1))
        for m in re.finditer(STMT + r"git[ \t]+(?:-[cC][ \t]+\S+[ \t]+)*commit\b([^;&|\n]*)", command, re.M)
    )


def _codex_review_stdin(command: str, _cwd: str) -> bool:
    """`codex review` without `< /dev/null` waits silently on stdin."""
    return any("/dev/null" not in m.group(1) for m in re.finditer(STMT + r"codex[ \t]+review\b([^;&|\n]*)", command, re.M))


RULES: tuple[Rule, ...] = (
    Rule("zsh-set-unquoted", "deny", "`set -- $var` does not word-split in zsh",
         "use an array (`args=(a b); set -- \"${args[@]}\"`) or loop with `while IFS= read -r x`",
         pat(STMT + r"set[ \t]+--[ \t]+\$\{?[A-Za-z_]\w*\}?(?=[\s;&|)]|$)"),
         ("for s in 'a 1'; do set -- $s; done",), ('set -- "$@"', "set -- a b"), zsh_only=True),
    Rule("zsh-for-scalar", "warn", "`for x in $var` iterates once over a scalar in zsh",
         "iterate an array (`\"${arr[@]}\"`), a glob, or `while IFS= read -r x` over the lines",
         pat(r"\bfor[ \t]+\w+[ \t]+in[ \t]+\$\{?[A-Za-z_]\w*\}?[ \t]*(?:;|\n|$)"),
         ("for f in $files; do echo $f; done",),
         ('for f in "${files[@]}"; do :; done', "for f in $(ls); do :; done", "for f in a b; do :; done"), zsh_only=True),
    Rule("zsh-unquoted-list-var", "warn", "a multi-line `$(...)` result is passed unquoted, so zsh sends it as one word",
         "build an array, pass globs, or use `xargs`/`while IFS= read -r`; never `cmd $LIST`",
         _unquoted_list_var,
         ('F="$(ls tests | grep id)"; pytest $F', "files=$(git diff --name-only); git add $files"),
         ('F="$(ls)"; echo "$F"', "n=$(git rev-parse HEAD); echo $n", 'F="$(ls)"; printf "%s\\n" $F'), zsh_only=True),
    Rule("zsh-command-in-variable", "deny", "a command line stored in a string variable is not split into words by zsh",
         "use a function or an array (`GIT=(git -C dir); \"${GIT[@]}\" status`)",
         _command_in_variable, ('GIT="git -C /x"; $GIT status',),
         ('X="git"; echo "$X"', 'GIT=(git -C /x); "${GIT[@]}" status'), zsh_only=True),
    Rule("zsh-reserved-var", "deny", "assigning `status`, `path`, `argv`... clobbers a zsh special parameter",
         "rename it (`job_status`, `file_path`); `path` is tied to PATH and breaks every later command",
         lambda c, _cwd: bool(
             re.search(STMT + r"(?:(?:local|typeset|declare|export|readonly)[ \t]+(?:-\w+[ \t]+)*)?(?:" + RESERVED + r")=(?!=)", c, re.M)
             or re.search(r"\bfor[ \t]+(?:" + RESERVED + r")[ \t]+in\b", c)
             or re.search(r"\bread[ \t]+(?:-\w+[ \t]+)*(?:" + RESERVED + r")\b(?!\w)", c)),
         ("status=$?; echo $status", "path=$(pwd); ls", "while IFS= read -r path; do :; done < f",
          "for path in a b; do :; done", "local status=1"),
         ("job_status=$?", "my_path=$(pwd)", 'export PATH="$PATH:/x"', "echo path=$x"), zsh_only=True),
    Rule("zsh-unmatched-glob", "warn", "an unquoted glob with no match aborts the whole command in zsh (`no matches found`)",
         "quote the pattern for the tool, use `find`, or add `(N)`; check the files exist first",
         _unmatched_glob, ("ls *.zzz",), ("ls *.txt", 'ls "*.zzz"', "make && ls *.zzz", "touch a.zzz; ls *.zzz"), zsh_only=True),
    Rule("zsh-colon-modifier", "warn", "`$var:x` starts a history-style modifier in zsh (`$sha:src/a.py` is rewritten)",
         "brace the name: `\"${sha}:src/a.py\"`",
         pat(r"\$[A-Za-z_]\w*:[ahrestluAQqxfFg&]"),
         ('git show "$sha:src/a.py"',), ('git show "${sha}:src/a.py"', 'echo "$PATH:/x"'), zsh_only=True),
    Rule("git-worktree-relative", "warn", "`git -C <repo> worktree add <relative>` resolves the path from <repo>, not the shell",
         "pass an absolute path, then `git -C <repo> status` to confirm the checkout stayed clean",
         pat(STMT + r"git[ \t]+-C[ \t]+\S+[ \t]+worktree[ \t]+add[ \t]+(?:-\w+[ \t]+(?:\S+[ \t]+)?)?(?![/~$\"'-])\S"),
         ("git -C /repo worktree add ../x -b y",), ("git -C /repo worktree add /abs/x -b y", "git -C /repo status")),
    Rule("echo-backslash", "deny", "zsh and BSD `echo` interpret backslash sequences (`\\copy`, `\\n`) inside quotes",
         "use `printf '%s\\n' 'text'` for literal text",
         pat(STMT + r"""echo[ \t]+(?:-\w+[ \t]+)*(?:"[^"\n]*\\[A-Za-z][^"\n]*"|'[^'\n]*\\[A-Za-z][^'\n]*')"""),
         (r'echo "\copy t from f"', r"echo '\n'"), (r'printf "%s\n" "\copy t"', 'echo "hello"')),
    Rule("bsd-cat-A", "deny", "macOS `cat` has no `-A`", "use `cat -et file` or `od -c file | head`",
         pat(STMT + r"cat[ \t]+(?:-\w+[ \t]+)*-\w*A\w*"), ("cat -A file",), ("cat -et file", "cat file")),
    Rule("bsd-grep-P", "deny", "macOS `grep` has no `-P` (Perl regex)", "use `grep -E`, `rg -P`, or `git grep -P`",
         pat(STMT + r"grep[ \t]+(?:-\S+[ \t]+)*-\w*P\w*"),
         ("grep -P '\\d+' f", "ls | grep -oP 'a'"), ("git grep -P 'a'", "rg -P 'a'", "grep -E 'a' f")),
    Rule("bsd-sed-inplace", "deny", "BSD `sed -i` needs a suffix argument; `sed -i 's/a/b/' f` fails",
         "use `sed -i '' 's/a/b/' f`, or write with python3",
         pat(r"\bsed[ \t]+(?:-[A-Za-z]+[ \t]+)*-i[ \t]+(?!''|\"\")"),
         ("sed -i 's/a/b/' f", "sed -i -e 's/a/b/' f"),
         ("sed -i '' 's/a/b/' f", "sed -i.bak 's/a/b/' f", "sed 's/a/b/' f")),
    Rule("bsd-sed-word-boundary", "warn", "BSD `sed` has no `\\b` word boundary", "use `[[:<:]]`/`[[:>:]]`, or python3",
         pat(r"\bsed\b[^|;\n]*\\b"), (r"sed 's/\bfoo\b/x/' f",), ("sed 's/foo/x/' f", "sed -E 's/foo|bar/x/' f")),
    Rule("secret-env-dump", "deny", "dumping the environment prints every secret in it",
         "list names only (`env | cut -d= -f1`) or test one value (`printenv NAME | wc -c`)",
         _env_dump, ("env | grep -i url", "printenv", "export -p | grep DB"),
         ("env FOO=1 python3 x.py", "printenv HOME", "env | cut -d= -f1", "env | wc -l")),
    Rule("secret-file-read", "warn", "reading a credentials or `.env` file prints its values",
         "count or list keys (`grep -c`, `cut -d= -f1`) and never paste the values",
         pat(r"\b(?:cat|head|tail|less|more|bat)[ \t]+[^|;&\n]*(?:\.env(?:\.\w+)?\b|\.netrc|credentials|id_rsa|id_ed25519|\.pem\b|\.gbrain/config\.json|\.aws/|\.ssh/)"),
         ("cat ~/.gbrain/config.json", "head -3 .env"), ("cat README.md", "ls ~/.ssh", "grep -c KEY .env")),
    Rule("git-interactive", "deny", "interactive git commands wait for a terminal that is not there",
         "use non-interactive forms (`git add <paths>`, `git rebase <base>`, `git diff`)",
         pat(STMT + r"git[ \t]+(?:rebase[ \t]+(?:-\S+[ \t]+)*(?:-i\b|--interactive)|add[ \t]+(?:-\S+[ \t]+)*(?:-[pi]\b|--patch|--interactive)|(?:mergetool|difftool)\b)"),
         ("git rebase -i HEAD~3", "git add -p", "git difftool"), ("git rebase origin/main", "git add -A", "git diff --stat")),
    Rule("git-commit-no-message", "deny", "`git commit` without a message opens an editor and hangs",
         "pass `-m \"msg\"` or `-F -` with a heredoc, or `--no-edit` when amending",
         _commit_without_message, ("git commit", "git commit -a", "git commit --amend"),
         ("git commit -m x", "git commit -q -F -", "git commit --amend --no-edit", 'git commit -am "x"', "git commit -qm x")),
    Rule("codex-review-stdin", "deny", "`codex review` blocks silently on stdin", "end the command with `< /dev/null`",
         _codex_review_stdin, ('codex review "x"',), ('codex review "x" < /dev/null',)),
    Rule("kill-by-pattern", "warn", "`pkill -f` and `kill $(pgrep -f ...)` match the wrapper shell and this command itself",
         "match with a bracket (`pgrep -f '[s]erver'`), use a pid file, or kill a known pid",
         pat(STMT + r"pkill[ \t]+-f\b|\bkill[ \t]+(?:-\w+[ \t]+)*\$\([ \t]*pgrep[ \t]+-f"),
         ("pkill -f server", "kill $(pgrep -f server)"), ("kill 1234", "pgrep -f '[s]erver'")),
    Rule("bash4-in-zsh", "deny", "`${var,,}`, `${var^^}`, `mapfile` and `readarray` are bash 4+; they fail in zsh and bash 3.2",
         "use `tr '[:upper:]' '[:lower:]'` and `while IFS= read -r line`",
         pat(r"\$\{[A-Za-z_]\w*(?:,,|\^\^|,|\^)\}|\bmapfile\b|\breadarray\b"),
         ("x=${y,,}", "mapfile -t a < f"), ("x=$(echo \"$y\" | tr A-Z a-z)", "echo ok"), zsh_only=True),
    Rule("gnu-only-flags", "deny", "GNU-only flags that BSD tools on macOS reject (`date -d`, `stat -c`, `find -printf`, ...)",
         "use `date -v`, `stat -f`, `python3`, `base64 | tr -d '\\n'`, `sed '$d'`, `xargs -0`",
         pat(r"\bdate[ \t]+(?:-\w+[ \t]+)*-d\b|\bstat[ \t]+(?:-\w+[ \t]+)*-c\b|\bfind\b[^|;\n]*-printf\b|\bbase64[ \t]+(?:-\w+[ \t]+)*-w\d*(?=[ \t]|$)|\bhead[ \t]+-n[ \t]*-\d|\bxargs[ \t]+(?:-\w+[ \t]+)*-d\b"),
         ("date -d yesterday", "stat -c %s f", "find . -printf '%p'", "base64 -w0 f", "head -n -1 f", "xargs -d x ls"),
         ("date -v-1d", "stat -f %z f", "head -n 5 f", "xargs -0 ls")),
    Rule("bsd-date-nanoseconds", "warn", "BSD `date` has no `%N`; it prints a literal `N`", "use python3 `time.time_ns()`",
         pat(r"\bdate\b[^|;\n]*%N"), ("date +%s%N",), ("date +%s",)),
)


def strip_heredocs(command: str) -> str:
    """Drop heredoc bodies: they are data for another program, not commands to lint."""
    return HEREDOC.sub(lambda m: m.group(0).split("\n", 1)[0], command)


def evaluate(command: str, cwd: str) -> list[Rule]:
    """Return the rules that fire for *command*, after the escape marker and bash-body skips."""
    escaped = {i for m in ESCAPE.finditer(command) for i in m.group(1).split(",")}
    if escaped & {"all", "*"}:
        return []
    body_is_bash = bool(BASH_BODY.search(command))
    stripped = strip_heredocs(command)
    return [
        rule for rule in RULES
        if rule.id not in escaped and not (rule.zsh_only and body_is_bash) and rule.check(stripped, cwd)
    ]


def markdown() -> str:
    """Render the rule table embedded in shell-hygiene/SKILL.md."""
    lines = ["| Rule | Level | What goes wrong | Fix |", "| --- | --- | --- | --- |"]
    for r in RULES:
        lines.append(f"| `{r.id}` | {r.level} | {r.summary} | {r.hint} |".replace("|`", "|`"))
    return "\n".join(lines)


def self_test() -> int:
    """Run every rule's fixtures in a scratch directory; return the number of failures."""
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "exists.txt"), "w", encoding="utf-8").close()
        for rule in RULES:
            for case, should_fire in [(b, True) for b in rule.bad] + [(g, False) for g in rule.good]:
                fired = rule.id in {r.id for r in evaluate(case, tmp)}
                if fired != should_fire:
                    failures += 1
                    print(f"FAIL {rule.id}: {'missed' if should_fire else 'false positive on'}: {case}", file=sys.stderr)
    print(f"shell-gotchas self-test: {len(RULES)} rules, {failures} failure(s)")
    return failures


def log_path() -> str:
    """The usage log: SHELL_GOTCHAS_LOG, else the user's state directory (never the Claude config dir)."""
    explicit = os.environ.get("SHELL_GOTCHAS_LOG")
    if explicit:
        return explicit
    state = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(state, "shell-gotchas", "usage.log")


def _log(rules: list[Rule], command: str, mode: str) -> None:
    """Append rule ids and a command hash to the usage log; never the command text."""
    path = log_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        entry = {"ts": int(time.time()), "mode": mode, "rules": [r.id for r in rules],
                 "cmd": hashlib.sha256(command.encode("utf-8")).hexdigest()[:12]}
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def report() -> int:
    """Print how often each rule fired, from the usage log, to tune or demote noisy rules."""
    path = log_path()
    counts: dict[str, int] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                for rule_id in json.loads(line).get("rules", []):
                    counts[rule_id] = counts.get(rule_id, 0) + 1
    except (OSError, ValueError):
        pass
    for rule_id, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"{n:5d}  {rule_id}")
    print(f"{sum(counts.values())} firing(s) across {len(counts)} rule(s) in {path}")
    return 0


def main(argv: list[str]) -> int:
    """Hook entry point: read the PreToolUse payload and block or warn."""
    if "--report" in argv:
        return report()
    if "--markdown" in argv:
        print(markdown())
        return 0
    if "--self-test" in argv:
        return 1 if self_test() else 0
    mode = os.environ.get("SHELL_GOTCHAS_MODE", "enforce")
    if mode == "off":
        return 0
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    command = (data.get("tool_input") or {}).get("command") or ""
    if not command:
        return 0
    fired = evaluate(command, data.get("cwd") or os.getcwd())
    if not fired:
        return 0
    _log(fired, command, mode)
    blocking = [r for r in fired if r.level == "deny" and mode == "enforce"]
    lines = [f"  [{r.id}] {r.summary} -- {r.hint}" for r in fired]
    escape = "If the command is correct as written, add `# gotcha-ok: <rule-id>` to it."
    if blocking:
        sys.stderr.write("BLOCKED by shell-gotchas (zsh/macOS shell traps); fix the command and retry:\n"
                         + "\n".join(lines) + "\n" + escape + "\n")
        return 2
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "additionalContext": "shell-gotchas warning:\n" + "\n".join(lines)}}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
