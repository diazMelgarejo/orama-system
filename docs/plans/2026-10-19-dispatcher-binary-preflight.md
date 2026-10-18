# Dispatcher executable discovery

## Contract

The dispatcher delegates durable jobs and process execution to PT. Its binary
registry answers one local question before dispatch: which executable would an
operator select for a registered adapter? It does not establish a new process
runner or duplicate PT's provider contracts.

The registry contains immutable pairs of environment variable and executable
name. Discovery follows explicit override, registered environment override,
then PATH. A configured override that is empty, missing, a directory, or not
executable fails; it never silently falls back to another installation.
Command strings are interpreted as a single executable name or pathname,
never a shell command. Spaces in executable paths remain intact.
On Windows, the resolved suffix must be permitted by `PATHEXT`, including on
older Python versions that accept arbitrary directly named regular files.

The standalone consumer is `python3 -m bin.agents.dispatcher --check-binary
<agent> [--binary-path <file>]`. Success emits JSON containing `binary` and
`path` with exit 0. Invalid configuration emits a repair message to stderr
with exit 2. No executable is launched during this check.

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
actual adapter command names, immutable registrations, malformed and
non-executable overrides, paths containing spaces, unknown adapters,
machine-readable results, and failure diagnostics. Existing bridge tests
continue to check the verifier gate and PT dispatch boundary.

## Sources

- [Dispatcher](../../bin/agents/dispatcher.py)
- [Agent staging and operator commands](../../bin/agents/README.md)
- [Bridge tests](../../tests/test_bridge.py)
- [Executable discovery tests](../../tests/test_dispatcher_binary_registry.py)
