# Claude-Desktop-LLM provider-native observability boundary

**Date:** 2026-08-29  
**Status:** cross-repository architecture clarification  
**Applies to:** Claude-Desktop-LLM modernization, Agate local-metal planning, PT unbundling
references, and future MCP v2 integration planning

## Canonical correction

OpenTelemetry is explicitly out of scope for `diazMelgarejo/Claude-Desktop-LLM` **because
observability should target Ollama and LM Studio directly through their native runtime/provider
surfaces**.

This rule concerns the observability implementation only. It MUST NOT be interpreted as a change
to the target Claude-Desktop-LLM architecture.

Retain:

```text
entrypoints / MCP transport
        |
canonical TypeScript implementation
        |
canonical tool registry
        |
effect policy + endpoint policy
        |
provider contract
   /            \
Ollama adapter   LM Studio adapter
   |                 |
Ollama runtime    LM Studio runtime
```

Provider-native observability attaches at the Ollama and LM Studio runtime/provider boundaries.

## Provider-native evidence

The implementation should prefer native runtime/model evidence from Ollama and LM Studio for the
subset actually needed by the product, such as:

- health and availability;
- loaded-model state;
- provider/model lifecycle where exposed;
- request outcome and provider errors;
- native usage/timing where exposed;
- local runtime/compute state useful for diagnosis.

A normalized cross-provider diagnostic view MAY be added when it is useful.

A redacted local JSONL/audit record MAY exist as secondary evidence.

Neither becomes the source observability authority.

Explicitly absent from the target:

```text
OpenTelemetry SDK
OTLP exporter
Collector topology
generic telemetry backend requirement
```

PT's OTel implementation remains valid for PT. Claude-Desktop-LLM may reuse redaction or
evidence-design lessons but MUST NOT cargo-cult PT's exporter stack.

## Relationship to Agate

`oramasys/agate` owns the cold-local-metal hardware capability, model-fit, affinity, routing, and
hard placement/resource-constraint contract.

Agate is MHS-convergent, not presently MHS-conformant while the Model Hardware Standard remains a
research preview.

Claude-Desktop-LLM owns the canonical local runtime/provider control boundary for Ollama and LM
Studio.

```text
Agate
  where may/should the model run?
        |
        v
Claude-Desktop-LLM
  how is the selected local runtime operated?
        |
   +----+----+
   |         |
Ollama   LM Studio
```

No lower layer should absorb another layer's authority merely because the systems are deployed
together.

## MCP v2 sequencing

MCP v2 work for Claude-Desktop-LLM is blocked and unscheduled until the Orama and Perpetua v2
migration into `oramasys/*` is complete and the resulting authority handoffs and integration
contracts are merged and authoritative.

Therefore:

- do not design Claude-Desktop-LLM around speculative MCP v2 APIs now;
- do not introduce compatibility shims merely to anticipate unfinished v2 contracts;
- continue security, canonicalization, provider, testing, packaging, and provider-native
  observability work independently of that protocol migration.

## Storage-plan correction

The prepared Phase-1 patch is authoritative over the stale ASCII-only storage-name regex present
in older planning text.

The implementation permits ordinary spaces, Unicode, and internal dots while rejecting separators,
control characters, Windows-reserved names, trailing dot/space, and containment escape, followed
by resolved-parent containment verification.

Do not regress it to an ASCII-only regex merely to make older documents match.

## Governance rule

```text
technology exclusion != architecture deletion
provider-native observability != provider-contract deletion
secondary JSONL evidence != observability authority
blocked/deferred != rejected
MHS convergence != current MHS conformance
```

If older Claude-Desktop-LLM planning documents conflict with this reference, they should be updated
or explicitly marked superseded rather than left co-authoritative.
