# Plan Integration Reference

> **Role:** Merge multiple Hermes- or operator-authored plans into one canonical plan.
> **Absorbed from:** Hermes-local `hermes-harness` self-improve fork (2026-07-23).

Use when asked to synthesize multiple planning documents into one canonical plan for
Hermes onboarding or related orama-system work.

## Reproduction pattern

1. Read each source plan document in full.
2. Read the existing target plan document in full.
3. Reframe absorption targets or canonical sources that do not exist in `main` as
   no-ops; enrich existing canonical artifacts instead.
4. Convert machine-specific paths to repo-relative canonical paths (LINT-006).
5. Produce a single cohesive plan with provenance, measurable goals, risks, success
   metrics, and an approval gate.
6. Do not delete or overwrite source plans; improve only the intended target plan.

## Rule set (operating thesis)

1. **Reframe, don't recreate** — missing canonical targets → no-op + enrich what exists.
2. **Repo-relative only** — no Windows-local absolute paths in tracked content.
3. **Additive migration** — new artifacts coexist until verified; redirect after parity.
4. **Preserve provenance** — source filenames and context in a Provenance section.
5. **Single helper pattern** — one shared helper for repeated platform logic.
6. **Parametrize endpoints** — machine IPs via env vars (`$MAC_IP`, `$WIN_IP`); never hardcode LAN IPs.
7. **Localhost-when-local** — own-machine services use `localhost`; cross-machine uses env IPs.

## Quality gates

- Target plan exists and is improved in place.
- No new files unless explicitly requested.
- Repo-relative paths throughout.
- Source content preserved honestly in provenance or incorporated sections.

## Related

- [`../SKILL.md`](../SKILL.md) § Boundaries — plan integration in Always Do
- [`hermes-skill-absorption-map.md`](hermes-skill-absorption-map.md) — absorption targets
