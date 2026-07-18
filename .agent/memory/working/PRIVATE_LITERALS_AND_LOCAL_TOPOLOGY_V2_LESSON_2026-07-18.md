# Private Literals And Local Topology V2 Lesson

Date: 2026-07-18
Scope: orama-system, Perpetua-Tools
Status: cross-repo operational memory

## Rule

Continue adding durable `.agent` memory and repository lessons, but never place
private owner identity literals, forbidden attribution literals, workstation
specific paths, or live LAN topology in tracked files.

The repository may contain:

- policy text describing the category of values that are forbidden;
- loader code that reads local-only values at runtime;
- synthetic tests proving the guard behavior;
- documentation that points to the local-only mechanism without quoting values.

The repository must not contain:

- the actual private literals;
- encoded forms of the private literals;
- real LAN/device endpoints as tracked defaults;
- commit messages or PR templates that quote private identity values.

## Local-Only Placement Pattern

The actual private values belong outside the repos in the OpenClaw workspace root
local-only configuration. The repos only know how to discover that file and how
to fail closed when a tracked file contains a forbidden value.

Live device topology belongs in ignored env or runtime-state files, not tracked
YAML or docs. Tests must use synthetic examples instead of real operator data.

## Cross-Repo Implication

This is a shared invariant between Orama and Perpetua-Tools. If one repo changes
the guard behavior, the other should be reviewed for parity before declaring the
work complete.

Use repo-relative references in docs and memory. Avoid absolute workstation
paths even when recording the recovery story.

## Checklist

- Run a case-insensitive tracked-file scan for forbidden categories.
- Include encoded-form scans when a prior guard used encoding.
- Keep `.agent/memory/**` active, sanitized, and committed when it records a
  durable lesson.
- Keep actual values in local-only files outside tracked repos.
- Run repo hygiene after edits.
- Treat already-pushed history cleanup as a separate explicit operation.

## Short Rule

Tracked repos may know how to find private/local values. They must not contain
the values.
