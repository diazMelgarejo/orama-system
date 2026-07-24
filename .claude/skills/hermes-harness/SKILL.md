---
name: hermes-harness
description: >-
  Onboards Hermes Agent as a cross-harness operator shell for PT-orama and ECC
  workflows. Use when installing Hermes, importing ECC/orama skills into Hermes,
  configuring Nous Portal or LM Studio providers, adding Hermes beside OpenClaw,
  or dispatching Hermes, Gemini, AGY, and Codex CLI coding partners.
version: 1.1.0.0
license: Apache 2.0
compatibility: hermes, codex, claude-code, windows, openclaw, ecc, agy
agent_compatibility:
  - Hermes
  - Codex
  - Claude
  - OpenClaw
  - AGY
  - Cursor
layer: "1 — Operator shell (pairs with openclaw-skills fabric)"
upstream: https://github.com/NousResearch/hermes-agent
upstream_path: $HERMES_HOME/hermes-agent
parent_skill: orama-system
origin: ECC Hermes setup, Hermes/OpenClaw migration, and cross-harness docs
triggers:
  - hermes setup
  - hermes onboarding
  - nous portal
  - hermes openclaw migration
  - ecc harness
  - cross-harness
  - install codex cli on windows
allowed-tools: bash, file-operations, web-search
---

<!-- THIN-WRAPPER: canonical skill lives in orama-system/bin/orama-system -->

# hermes-harness (thin wrapper)

Canonical, permanent implementation: `../../../bin/orama-system/skills/hermes-harness/`.
**Read it before proceeding** — this wrapper only carries discovery metadata.

Pre-wrapper body preserved at `SKILL.md.premerge-20260722.bak`.
