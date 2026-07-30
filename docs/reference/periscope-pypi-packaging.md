# Periscope / AgentsView — PyPI Packaging (reference)

> **Quadrant:** Reference. **Applies to:** `diazMelgarejo/periscope` release CI.
> **Status:** PyPI publish step exists in CI but is disabled — name collision, not a
> build/pipeline problem. See § Current status before re-enabling.

## Current status (as of 2026-05-14, needs revalidation)

The full release pipeline (Docker, Go-binary release, Desktop Release, PyPI publish)
was built and all four workflows went green on tag `v0.29.2-periscope.2-945bda3` —
**except PyPI publish, which is explicitly disabled**:

> The `periscope` package name on PyPI is already taken by an unrelated project
> (Patrick Dessalle, v0.2.4).

Recorded in [`docs/NEXT_STEPS.md`](../NEXT_STEPS.md) § CI State / § User Action Queue
item A. The gate is a repo variable, `ENABLE_PYPI_PUBLISH`, defaulting to unset/false —
this was a deliberate pause, not a broken build. Two options were left open and neither
has been executed:

1. **Leave it disabled** — ship via GitHub Releases only (current state; Go binaries +
   wheels still build in CI, they just don't upload to PyPI).
2. **Rename the package** (e.g. `periscope-viewer`) and re-enable with an OIDC trusted
   publisher.

**Before doing anything else:** re-check whether `periscope` is still taken on PyPI —
name availability can change — and decide on option 1 vs 2 with the current maintainer
before flipping `ENABLE_PYPI_PUBLISH`.

The related commit [`72431d3b`](https://github.com/diazMelgarejo/periscope/commit/72431d3b6540f59d203f29eca7245371c829a106)
("fix(ci): make desktop-release signing steps conditional on secrets") is from the same
CI-hardening effort and flags "configure PyPI OIDC trusted publisher" as outstanding
user action in its commit message — it did not itself resolve the name collision.

## Standard modern PyPI build/publish practice (for when this is re-enabled)

Confirmed against the current Python Packaging User Guide, PyPI's own trusted-publishing
docs, and the `pypa/gh-action-pypi-publish` action docs (checked 2026-07-24):

- **Structure:** `src/` layout; `pyproject.toml` with a `[build-system]` table
  (`setuptools>=68` or `hatchling`) and a `[project]` metadata table — no `setup.py`.
- **Build:** `pip install build && python -m build` → wheel + sdist in `dist/`.
- **Validate:** `python -m twine check dist/*` before anything else.
- **Rehearse on TestPyPI first:** separate account/project from production PyPI;
  `twine upload --repository testpypi dist/*`, then install the wheel in a clean env
  and smoke-test imports.
- **Publish via CI with Trusted Publishing (OIDC), not a stored API token:**
  1. Register a Trusted Publisher on PyPI for the project — the GitHub owner,
     repository, exact workflow filename, and (recommended) environment name must all
     match exactly, or the publish is rejected.
  2. Two-job workflow: a `build` job produces `dist/` and uploads it as a GitHub
     Actions artifact; a separate `publish` job (gated on a tag push or a published
     GitHub Release) has `permissions: id-token: write` and `environment: pypi`, then
     calls `pypa/gh-action-pypi-publish@release/v1` with no username/password.
  3. **Keep build and publish in separate jobs.** This is the security-recommended
     shape, not a style preference — a compromised build step in the same job as the
     publish step could exfiltrate the OIDC-derived token; separating jobs means the
     build step never has publish privileges.
- **Versioning:** semver (`MAJOR.MINOR.PATCH`); the `pyproject.toml` version, the git
  tag, and the release notes must agree. PyPI refuses to let you re-upload files for a
  version that already exists — bump and rebuild, never try to overwrite.

## What this does NOT cover

Periscope also ships **Go binaries** (see the "Release (go binaries + wheels)"
workflow) and a **Tauri desktop app** (see the Desktop Release workflow and
[`docs/NEXT_STEPS.md`](../NEXT_STEPS.md) § B/C for updater signing and Apple code
signing). Those are separate release surfaces from the PyPI wheel publish step this
doc covers — check the actual `.github/workflows/` files in the periscope repo for how
the wheel build step feeds distribution artifacts alongside the Go binaries before
assuming this doc's generic `python -m build` flow maps 1:1 onto periscope's existing
workflow file.

## Related

- [`docs/NEXT_STEPS.md`](../NEXT_STEPS.md) § CI State / § User Action Queue item A —
  original historical record this doc expands on; dated 2026-05-14, needs revalidation
  against current periscope CI state before acting.
- [`docs/plans/2026-05-24-periscope-l4-integration-plan.md`](../plans/2026-05-24-periscope-l4-integration-plan.md)
  § Revised Phase A — operational maintenance table.
- [`docs/plans/2026-07-28-periscope-lineage-modernization-epic.md`](../plans/2026-07-28-periscope-lineage-modernization-epic.md) —
  a separate, unrelated periscope epic (git history, not packaging); linked here only
  because it's the other active periscope planning doc a reader may already have open.
- [`docs/reference/periscope-cursor-repo-rules.md`](periscope-cursor-repo-rules.md) —
  Cursor-specific repo rules for the periscope checkout; unrelated to PyPI but same doc
  family.
