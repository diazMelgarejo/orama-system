# Dispatcher executable discovery

> **Status:** implemented in PR #423 (2026-10-19). A plan record for a narrow local command,
> not a decision record; durable decisions live in `docs/v2/`.

## Contract

The dispatcher delegates durable jobs and process execution to PT. Its binary
registry answers one local question before dispatch: which executable would an
operator select for a registered adapter? It does not establish a new process
runner or duplicate PT's provider contracts.

The registry contains immutable pairs of environment variable and executable
name for the nine CLI agents the dispatcher can name: Antigravity (`agy`),
Gemini, Codex, Cursor (`cursor-agent`), Claude, Ollama, Windsurf, Cline (the Relay
adapter) and Kimi (the Nova adapter). Adding an agent is one registry entry plus
one row in the expected-command table of the test. Discovery follows explicit
override, registered environment override, then PATH. A configured override that
is empty, missing, a directory, or not executable fails; it never silently falls
back to another installation.
Command strings are interpreted as a single executable name or pathname,
never a shell command. Spaces in executable paths remain intact. A leading `~`
is expanded. A value containing a path separator is a pathname resolved as
given, so a relative one such as `./agent` depends on the current directory. A
bare name is looked up on `PATH` only: a hit outside a listed `PATH` directory
is refused, which stops Windows from preferring a binary planted in the working
directory, and an empty `PATH` entry (read by a shell as the current directory)
is not trusted; quotes around a `PATH` entry (common on Windows) are ignored.
On Windows, the resolved suffix must be permitted by `PATHEXT`, checked here
rather than trusting the interpreter's `shutil.which`, because some versions
accept arbitrary directly named regular files. Continuous integration runs on
Linux only (Python 3.12), so the Windows branches are exercised by simulating
the platform, not on a Windows runner; treat them as unproven there.

The standalone consumer is `python3 -m bin.agents.dispatcher --check-binary
<agent> [--binary-path <file>]`. Success emits JSON containing `binary` and
`path` with exit 0. Invalid configuration emits a repair message to stderr
with exit 2. An unregistered agent is rejected earlier by the argument parser
(`invalid choice`, usage on stderr, exit 2, nothing on stdout), so the
resolver's own "unknown binary" error is reachable only from Python callers.
No executable is launched during this check.

## Ownership and limitations

- Orama owns the discovery registry and local preflight command.
- PT owns runtime arguments, prompt input, output parsing, job scheduling,
  containment, cancellation, and lifecycle evidence.
- Discovery proves availability at check time. It is neither executable
  attestation nor a guarantee that a later launch opens the same file.
- Agent presence does not prove authentication, provider compatibility,
  model availability, or authorization to dispatch.
- This change does not start an Ollama daemon or assume that every CLI
  accepts stdin prompts and emits JSON.

## Verification

`tests/test_dispatcher_binary_registry.py` checks override precedence,
actual adapter command names for every registration, a registry, test and
README drift guard, immutable registrations, malformed and non-executable
overrides on both the environment and explicit routes, paths containing spaces,
`~` expansion, relative pathnames, the working-directory and empty-`PATH`
refusals, unknown adapters, machine-readable results, and failure diagnostics. Existing bridge tests
continue to check the verifier gate and PT dispatch boundary.

## Sources

- [Dispatcher](../../bin/agents/dispatcher.py)
- [Agent staging and operator commands](../../bin/agents/README.md)
- [Bridge tests](../../tests/test_bridge.py)
- [Executable discovery tests](../../tests/test_dispatcher_binary_registry.py)
