export const meta = {
  name: "codex-openclaw-frugal-multimodel-review",
  description:
    "Frugal multi-resource feasibility plus Eng/DX review of the codex-openclaw-agent design.",
  phases: [
    {
      title: "Probe",
      detail: "Verify resource availability without spending remote calls or leaking secrets.",
    },
    {
      title: "Ground Facts",
      detail: "Verify OpenClaw provider shape and Codex backend reality from local repo/config evidence.",
    },
    {
      title: "Panel Review",
      detail: "Use one bounded lane each for Ollama, Codex, Gemini, AGY, OpenRouter, and AgentRouter.",
    },
    {
      title: "Synthesis",
      detail: "Dedupe, severity-rank, and run one local refutation pass on the top findings.",
    },
  ],
}

const RESOURCE_ORDER = ["ollama", "codex", "gemini", "agy", "openrouter", "agentrouter"]
const REVIEWED_DESIGN =
  "docs/superpowers/specs/2026-06-19-codex-openclaw-agent-design.md"
const DEFAULT_REFERENCE = "set OPENCLAW_REFERENCE to the local OpenClaw.md reference path"

function env(name, fallback = "") {
  if (typeof process === "undefined") return fallback
  return process.env?.[name] || fallback
}

function workflowPaths() {
  const repo = env("ORAMA_SYSTEM_ROOT", "orama-system")
  return {
    repo,
    spec: env("CODEX_OPENCLAW_SPEC", `${repo}/${REVIEWED_DESIGN}`),
    reference: env("OPENCLAW_REFERENCE", DEFAULT_REFERENCE),
  }
}

const PROBE_SCHEMA = {
  type: "object",
  properties: {
    resources: {
      type: "array",
      items: {
        type: "object",
        properties: {
          name: { type: "string" },
          available: { type: "boolean" },
          evidence: { type: "string" },
          model_or_route: { type: "string" },
          caveat: { type: "string" },
        },
        required: ["name", "available", "evidence"],
      },
    },
    notes: { type: "array", items: { type: "string" } },
  },
  required: ["resources", "notes"],
}

const LANE_REPORT = {
  type: "object",
  properties: {
    resource: { type: "string" },
    available: { type: "boolean" },
    resource_used: { type: "string" },
    cost_tier: { type: "number" },
    score: { type: "number" },
    score_rationale: { type: "string" },
    verified: {
      type: "array",
      items: {
        type: "object",
        properties: {
          claim: { type: "string" },
          evidence: { type: "string" },
        },
        required: ["claim", "evidence"],
      },
    },
    corrections: {
      type: "array",
      items: {
        type: "object",
        properties: {
          wrong_assumption: { type: "string" },
          correction: { type: "string" },
          evidence: { type: "string" },
        },
        required: ["wrong_assumption", "correction", "evidence"],
      },
    },
    findings: {
      type: "array",
      items: {
        type: "object",
        properties: {
          id: { type: "string" },
          title: { type: "string" },
          severity: { type: "string", enum: ["critical", "high", "medium", "low"] },
          lens: { type: "string" },
          detail: { type: "string" },
          fix: { type: "string" },
          ref: { type: "string" },
        },
        required: ["id", "title", "severity", "lens", "detail", "fix"],
      },
    },
    open_questions: { type: "array", items: { type: "string" } },
  },
  required: [
    "resource",
    "available",
    "resource_used",
    "cost_tier",
    "score",
    "score_rationale",
    "verified",
    "corrections",
    "findings",
    "open_questions",
  ],
}

const VERIFICATION_SCHEMA = {
  type: "object",
  properties: {
    verdicts: {
      type: "array",
      items: {
        type: "object",
        properties: {
          finding_id: { type: "string" },
          real: { type: "boolean" },
          confidence: { type: "number" },
          reason: { type: "string" },
        },
        required: ["finding_id", "real", "confidence", "reason"],
      },
    },
  },
  required: ["verdicts"],
}

function sharedContext(paths) {
  return `
TARGET: codex-openclaw-agent meta-skill in orama-system.

You are reviewing the corrected design, not the superseded draft. Do not re-report
resolved blockers unless the current design reintroduces them.

Corrected design to review:
- Spec: ${paths.spec}
- Optional reference: ${paths.reference}
- Repo: ${paths.repo}

Accepted design decisions:
- Skill path: bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/.
- Generated profile files include source-path and source-hash headers.
- Generated sections exist in CODEX.md, AGENTS.md, TOOLS.md, and SECURITY.md.
- CODEX.md is the generated binding/spec sheet; it is not one of OpenClaw's six
  native directive files. The generator must also update OpenClaw runtime files
  and openclaw.json model.primary.
- Backend binding is a first-class peer module:
  references/codex-backend-binding.md plus scripts/bind_codex_backend.sh.
- Resolver ladder: probe only, primary native plugin/onboard/session bind,
  idempotent install if safe, fallback to a local Codex app-server provider by
  reference, then verify backend identity is Codex/GPT and not Ollama.
- Auth is by reference only: never copy bearer tokens into generated files,
  refs, logs, prompts, or committed docs.
- Generated files write to the openclaw-home source repo, then stow. Never write
  generated files directly into the stow target.
- Source drift warns, continues, and regenerates marked sections when safe.
- Spawn mode supports ask, sub-agent, and standalone.
- Interactivity is normalized across interrupt envelopes, AskUserQuestion,
  terminal prompts/flags, and portal GUI controls.

Review for new issues only: architecture, resolver edge cases, security, tests,
determinism, regeneration behavior, interaction surfaces, and operator DX.
`
}

const REVIEW_RUBRIC = `
REVIEW RUBRIC:
- Architecture and module boundaries: bind_codex_backend as a peer module to
  hermes-harness; coupling to openclaw-new-agent overlay and profile generator;
  reuse by future Hermes/Gemini harnesses without leaking Codex-specific logic.
- Resolver correctness: stale app-server state files, plugin-present-but-broken,
  partial install, fallback when app-server is down, verify flakiness,
  concurrent regeneration, malformed generated markers, idempotent reruns.
- Security: auth-by-reference, no secret copies in CODEX.md/refs/logs, repo-
  relative paths, SECURITY.md operator ownership, source hashes as integrity not
  provenance.
- Tests and determinism: backend identity proves Codex-not-Ollama, golden files
  are stable across Mac/Windows, partial-write rollback, force blast radius, e2e
  smoke that OpenClaw actually invokes Codex.
- DX: time-to-hello-world, invisible success path, fail-loud messages with
  problem/cause/fix, recovery command, CLI flags, ask/sub-agent/standalone
  ergonomics, and one normalized interaction envelope.
`

const FRUGALITY_POLICY = `
FRUGALITY AND SAFETY RULES:
- Tier 0 first: use the already-provided context before any tool call.
- Tier 1 next: use local Ollama once when available.
- Use exactly one bounded review call per external resource lane:
  one Codex, one Gemini, one AGY, one OpenRouter, one AgentRouter.
- Do not parallel-fire extra web or paid calls from inside a lane.
- Do not echo bearer tokens, OAuth tokens, API keys, or raw auth config values.
- Do not commit, write files, delete files, deploy, or change accounts.
- Use read-only repo access. If a tool cannot run read-only, report unavailable.
- Use free or already-configured routes first. OpenRouter should use the free
  fallback stack unless the operator explicitly configured a different model.
- Respect ORAMASYS_OFFLINE=1: mark network lanes unavailable.
- Prefer gtimeout when present on macOS; otherwise use the current harness's
  bounded worker timeout. Never use sleep chains as a waiting strategy.
`

function probePrompt(paths) {
  return `${FRUGALITY_POLICY}

PROBE ONLY. Do not perform model completions except tiny version/status checks.
Work from repo ${paths.repo}.

Check these resources without printing secrets:
1. ollama: command exists and http://127.0.0.1:11434/api/tags responds; identify the first/default model.
2. codex: command exists and version/status can be checked without a model call.
3. gemini: command exists and version/status can be checked without a model call.
4. agy: command exists and version/status can be checked. Do not use --dangerously-skip-permissions.
5. openrouter: OPENROUTER_API_KEY exists and ORAMASYS_OFFLINE is not set. Do not print the key.
6. agentrouter: either an explicit AgentRouter route/env is configured, or OmniRoute exposes an AgentRouter route.
   Do not treat /usr/bin/ar as AgentRouter. If only OmniRoute is present but no AgentRouter route is verifiable,
   mark AgentRouter unavailable with that caveat.

Return a resource matrix only.`
}

function resourceAvailable(probe, name) {
  const resources = Array.isArray(probe?.resources) ? probe.resources : []
  return resources.some((r) => r.name === name && r.available)
}

function resourceEvidence(probe, name) {
  const resources = Array.isArray(probe?.resources) ? probe.resources : []
  return resources.find((r) => r.name === name) || { evidence: "not probed" }
}

function unavailableReport(name, probe) {
  const evidence = resourceEvidence(probe, name)
  return {
    resource: name,
    available: false,
    resource_used: "none",
    cost_tier: 0,
    score: 0,
    score_rationale: "resource unavailable",
    verified: [],
    corrections: [],
    findings: [],
    open_questions: [evidence.caveat || evidence.evidence || "resource unavailable"],
  }
}

function groundFactsPrompt(paths) {
  return `${sharedContext(paths)}
${FRUGALITY_POLICY}

GROUND FACTS LANE: local repo and config evidence.
Use local read-only evidence only. Do not call external models.

Answer with evidence:
1. How does OpenClaw define model providers and route model.primary?
2. What config shape registers an OpenAI-compatible provider for the Codex fallback?
3. Do openclaw plugins install, openclaw onboard --auth-choice openai-codex, and
   /cas_resume exist as real local commands/protocols here, or only as proposed
   design names?
4. Does the local Codex CLI expose or rely on an app-server endpoint? What state
   files or config prove that, without printing secrets?
5. How does the existing stack invoke Codex today, and are gpt-5.5 plus
   reasoning effort medium/xhigh represented in config structure?

Return JSON matching the lane report schema. Use resource="repo-grounded" and
resource_used="local repo/config read".`
}

function factBlock(reports) {
  const lines = []
  for (const report of reports) {
    for (const verified of report.verified || []) {
      lines.push(`[${report.resource}] FACT: ${verified.claim} (${verified.evidence})`)
    }
    for (const correction of report.corrections || []) {
      lines.push(
        `[${report.resource}] CORRECTION: ${correction.wrong_assumption} -> ${correction.correction} (${correction.evidence})`,
      )
    }
  }
  return lines.join("\n")
}

function lanePrompt(paths, probe, name, groundReports) {
  const context = sharedContext(paths)
  const evidence = resourceEvidence(probe, name)
  const facts = factBlock(groundReports)
  const base = `${context}
${FRUGALITY_POLICY}
${REVIEW_RUBRIC}

GROUND FACTS TO TREAT AS EVIDENCE:
${facts || "(none yet; be explicit about uncertainty)"}

RESOURCE LANE: ${name}
Probe evidence: ${JSON.stringify(evidence)}

Return JSON matching the schema. verified/corrections should cite file paths,
commands, or resource output summaries. findings should be new review issues only.
Also return score and score_rationale for this lane's confidence in the corrected design.`

  if (name === "ollama") {
    return `${base}

Use one local Ollama generation against the probed default model. Ask it for
failure modes in the backend resolver, generated-section merge behavior,
source-hash drift, and interaction-surface normalization. Keep the prompt short
and bias toward concrete edge cases over broad architecture commentary.
If Ollama is down, return available=false.`
  }

  if (name === "codex") {
    return `${base}

Use one read-only Codex CLI call from ${paths.repo}. Ask Codex to review the
backend-binding ladder, Codex app-server assumptions, generated profile design,
test plan, and backend identity verification. Use read-only sandboxing and no
file writes. If Codex cannot run, return available=false.`
  }

  if (name === "gemini") {
    return `${base}

Use one Gemini CLI or Gemini MCP call as a second-opinion analyzer for stale
commands, missing external/current-doc edge cases, and architecture/readability
risks. This is not the default reader lane; it is the explicit Gemini analyzer lane.`
  }

  if (name === "agy") {
    return `${base}

Use one AGY/Antigravity call as a bounded coding-partner review. Prefer
agy -p "/goal <bounded review prompt>". Do not use --dangerously-skip-permissions
unless AGY_ALLOW_PERMISSION_BYPASS=1 is explicitly set. If AGY exits 0 with
empty stdout, rerun once with a log file and then report unavailable if still empty.
Focus on hidden complexity, scope creep, and whether a generated profile can
actually bootstrap an OpenClaw runtime worker.`
  }

  if (name === "openrouter") {
    return `${base}

Use one OpenRouter call only if OPENROUTER_API_KEY is present and
ORAMASYS_OFFLINE is not set. Prefer the free model
nvidia/nemotron-3-super-120b-a12b:free, then another free fallback if needed.
Never print the key and do not choose a paid model by default. Focus on security,
determinism, and whether the resolver fails safely.`
  }

  return `${base}

Use one AgentRouter lane only if a real AgentRouter route is verified, either
directly via AGENTROUTER_* configuration or through OmniRoute exposing an
AgentRouter-backed route. Do not fake this through OpenRouter and do not use
/usr/bin/ar. If no distinct AgentRouter route is visible, return available=false.
Focus on orchestration optionality: standalone, sub-agent, ask-mode, and future
autoplan routing.`
}

function normalizeKey(finding) {
  const title = String(finding?.title || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
  const detail = String(finding?.detail || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
  return `${title.slice(0, 80)}|${detail.slice(0, 80)}`
}

function mergeFindings(reports) {
  const severityRank = { critical: 0, high: 1, medium: 2, low: 3 }
  const seen = new Map()

  for (const report of reports) {
    for (const finding of report.findings || []) {
      const key = normalizeKey(finding)
      if (!key || key === "|") continue
      const current = seen.get(key)
      const candidate = {
        ...finding,
        resource: report.resource,
        support: [report.resource],
      }
      if (!current) {
        seen.set(key, candidate)
        continue
      }
      current.support = Array.from(new Set([...(current.support || []), report.resource]))
      if ((severityRank[finding.severity] ?? 9) < (severityRank[current.severity] ?? 9)) {
        seen.set(key, { ...candidate, support: current.support })
      }
    }
  }

  return [...seen.values()].sort(
    (a, b) =>
      (severityRank[a.severity] ?? 9) - (severityRank[b.severity] ?? 9) ||
      String(a.title).localeCompare(String(b.title)),
  )
}

function verifyPrompt(paths, reports, topFindings) {
  const payload = JSON.stringify(topFindings, null, 2)
  return `${sharedContext(paths)}
${FRUGALITY_POLICY}

SYNTHESIS VERIFY PASS:
Use local/in-context reasoning only. Do not call Codex, Gemini, AGY, OpenRouter,
AgentRouter, or Ollama again. Refute weak findings and keep only issues that are
real in the corrected design.

Ground facts and corrections:
${factBlock(reports) || "(none)"}

Candidate findings:
${payload}

Return verdicts for every candidate finding id.`
}

export default async function runWorkflow(context = {}) {
  const agent = context.agent || globalThis.agent
  const parallel = context.parallel || globalThis.parallel
  const phase = context.phase || globalThis.phase || (() => {})
  const log = context.log || globalThis.log || (() => {})

  if (typeof agent !== "function" || typeof parallel !== "function") {
    throw new Error("workflow requires agent() and parallel() helpers")
  }

  const paths = workflowPaths()

  phase("Probe")
  const probe = await agent(probePrompt(paths), {
    model: "sonnet",
    agentType: "Explore",
    phase: "Probe",
    label: "probe:resources",
    schema: PROBE_SCHEMA,
  })

  const available = RESOURCE_ORDER.filter((name) => resourceAvailable(probe, name))
  log(`Resource probe: ${available.length}/${RESOURCE_ORDER.length} available (${available.join(", ") || "none"})`)

  phase("Ground Facts")
  const groundFacts = await agent(groundFactsPrompt(paths), {
    model: "sonnet",
    agentType: "Explore",
    phase: "Ground Facts",
    label: "facts:repo-grounded",
    schema: LANE_REPORT,
  })
  const groundReports = groundFacts ? [groundFacts] : []

  phase("Panel Review")
  const laneThunks = RESOURCE_ORDER.map((name) => async () => {
    if (!resourceAvailable(probe, name)) return unavailableReport(name, probe)
    return agent(lanePrompt(paths, probe, name, groundReports), {
      model: "sonnet",
      agentType: "Explore",
      phase: "Panel Review",
      label: `resource:${name}`,
      schema: LANE_REPORT,
    })
  })

  const reports = [...groundReports, ...(await parallel(laneThunks)).filter(Boolean)]
  const findings = mergeFindings(reports)
  const topFindings = findings
    .filter((f) => f.severity === "critical" || f.severity === "high")
    .slice(0, 6)

  log(
    `Panel review: ${reports.filter((r) => r.available).length} active lanes, ${findings.length} unique findings, verifying ${topFindings.length}`,
  )

  phase("Synthesis")
  const verification = await agent(verifyPrompt(paths, reports, topFindings), {
    model: "sonnet",
    phase: "Synthesis",
    label: "verify:top-findings",
    schema: VERIFICATION_SCHEMA,
  })

  const verdicts = new Map((verification.verdicts || []).map((v) => [v.finding_id, v]))
  const confirmed = topFindings.filter((f) => verdicts.get(f.id)?.real)
  const rejected = topFindings.length - confirmed.length

  return {
    resources: probe.resources,
    scores: reports.map((r) => ({
      resource: r.resource,
      score: r.score,
      rationale: r.score_rationale,
    })),
    fact_lines: factBlock(reports).split("\n").filter(Boolean),
    corrections: reports.flatMap((r) =>
      (r.corrections || []).map((c) => ({ ...c, resource: r.resource })),
    ),
    confirmed_findings: confirmed.map((f) => ({
      id: f.id,
      title: f.title,
      severity: f.severity,
      lens: f.lens,
      resource: f.resource,
      support: f.support,
      detail: f.detail,
      fix: f.fix,
      verification: verdicts.get(f.id),
    })),
    rejected_count: rejected,
    total_unique: findings.length,
    unavailable_resources: reports.filter((r) => !r.available).map((r) => r.resource),
  }
}
