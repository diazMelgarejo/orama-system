#!/usr/bin/env bash
# Delete only the manifest-approved, superseded Preserve-branch PR heads.
# This is intentionally inert unless an operator passes --execute.
set -euo pipefail

if [[ "${1:-}" != "--execute" ]]; then
  printf '%s\n' "Dry run only. Review docs/next/preserve-branch-manifest.md, then rerun: $0 --execute"
  exit 0
fi

repo="diazMelgarejo/orama-system"
tag_suffix="20260717"

# Newest activity first. #166 and #169 are intentionally absent: they need human review.
prs=(155 154 170 156 176 182 181 180 178 175 171 165 163 162 161 157 153 152 151 164 158 159 160 179 172)
branches=(
  "2026-07-12-001-gstack-safe-upgrade"
  "2026-07-11-002-gossip-bus-skill"
  "feat/agent-coordination-heartbeat-skill"
  "coderabbitai/utg/7e543a4"
  "skillify-pr2-followup"
  "subagent/win-orchestrator/doc-sync-peer-inbox"
  "subagent/win-coder/mac-co-orchestrator-playbook"
  "subagent/win-autoresearcher/h5-gpu-harness"
  "subagent/mac-researcher/h4-mac-benchmark"
  "skillify-pr1-standards-validator-plan"
  "feat/vitest-tdd-gate-scratch"
  "cursor/review-vitest-tdd-scratch-c4ae"
  "cursor/review-peer-inbox-docs-c4ae"
  "cursor/review-h4-mac-benchmark-c4ae"
  "cursor/oramasys-integrative-merge-c4ae"
  "cursor/ci-autofix-automation-1da6"
  "2026-06-30-start-windows-implementation"
  "2026-06-30-start-macos-implementation"
  "2026-06-27--windows-eol-turf-normalize"
  "cursor/review-self-reflection-c4ae"
  "cursor/ci-autofix-automation-b566"
  "cursor/ci-autofix-automation-d7b3"
  "cursor/fix-ci-hygiene-hermes-c4ae"
  "subagent/mac-researcher/h5-ollama-parallel"
  "fix/pr135-lint006-windows"
)

for i in "${!branches[@]}"; do
  pr="${prs[$i]}"
  branch="${branches[$i]}"
  tag="safety/preserve-pr-${pr}-${tag_suffix}"

  # A prior interruption is not a reason to retag or fail the entire batch.
  # Treat an already-deleted branch as completed; otherwise tag its current
  # remote head before issuing the deletion request.
  if ! git ls-remote --exit-code --heads origin "refs/heads/${branch}" >/dev/null 2>&1; then
    printf '%s\n' "already deleted: #${pr} ${branch}"
    continue
  fi

  git fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
  if ! git rev-parse --verify --quiet "refs/tags/${tag}" >/dev/null; then
    git tag "$tag" "origin/${branch}"
    git push origin "refs/tags/${tag}"
  fi
  gh api --method DELETE "repos/${repo}/git/refs/heads/${branch}"
done
