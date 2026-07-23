# Win — 2026-07-23 RTX 5080 dev environment reference published

**Job:** Cursor session — ECC install + session diagnosis consolidation  
**Status:** DONE (reference doc written + agent comms published)

## What landed

- **Canonical local reference doc** at workspace root:
  `win-rtx5080-windows-dev-reference.md` (sibling of orama-system checkout)
  — consolidates Node/npm fix, partner CLI paths, ECC Hermes+Cursor install,
  start.ps1 usage, anti-doxxing wiring, coord cycles 018–021, backlog state,
  errors resolved, and command cheat sheet.
- **ECC minimal profile installed:**
  - Hermes `~/.hermes` (454 ops, v2.0.0, 2026-07-23)
  - Cursor `orama-system/.cursor/` (481 ops, v2.0.0, 2026-07-23)
  - Thin wrappers: 5/5 verified via `install_hermes_thin_skills.py --install --verify`
  - `no-workstation-paths.mdc` preserved in orama `.cursor/rules/`
- **Node/npm diagnosis:** LM Studio bundled runtime on User PATH
  (`~/.lmstudio/bin`); node v25.5.0, npm v11.12.1

## Open / needs a peer or human

- **PT Cursor ECC install** not yet run (`install.ps1 --target cursor` from ecc-tools)
- **P5 PR #136** still 2/7 tasks on branch `cursor/security-pr3-swarm-approval-f559`
- **Mac H6 real-task** inbox item `mac-hypothesis-h6-real-task.md` awaiting follow-through
- **cursor-agent usage limits** caused manual branch completion for coord-021 coder jobs

## Not touched / explicitly deferred

- No code changes in this publish pass — documentation and agent comms only
- PT `.cursor/` ECC install deferred (see open items)
- P5 T3 launch verify deferred to feature branch work

## Pointer for Mac peer

Full reference: read `win-rtx5080-windows-dev-reference.md` on Win workspace root,
or fetch this drop from peer inbox. Key sections: ECC install commands, start.ps1
`--lan-peer` requirement, partner CLI PATH script, coord rinse pattern.
