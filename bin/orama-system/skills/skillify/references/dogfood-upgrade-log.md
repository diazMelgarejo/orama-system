# Dogfood Upgrade Log — skillify Upgrading Itself and oramasys-method

This is the audit trail and repeatable procedure for the self-referential
loop: skillify's own standards, plus Anthropic's skill-creator standards,
applied to skillify and to oramasys-method — including skillify's own
upgrade of itself. Read this before running the loop again on these two
skills or extending it to others.

## Why This File Exists

`skillify` produces other skills, but nothing previously checked skillify
(or its sibling `oramasys-method`) against its own Non-Negotiables and
against Anthropic's stricter packaged-skill schema. This file is the
record of the first such pass, kept as a `references/` card so the next
pass — on these two skills or any other — has a fixed procedure instead of
starting from memory.

## Procedure (repeat this for future dogfood passes)

1. **Read both standards before writing anything.** This repo's
   `references/skill-architecture-guide.md`,
   `skillify/references/modular-skill-authoring.md`,
   `skillify/references/skill-folder-template.md`, and Anthropic's
   skill-creator process (progressive disclosure, `<500` line ceiling,
   pushy trigger-rich `description`, golden-path examples).
2. **Diff, don't rewrite.** List what's actually missing against both
   standards before touching a working file. In this pass, both skills
   already had solid frontmatter, progressive disclosure, and Boundaries —
   the real gaps were: no `examples/`, no `eval/` folder, and no
   skill-creator-style `evals.json` test prompts.
3. **Name every standards conflict instead of silently picking one.**
   Found in this pass:
   - Anthropic's skill-creator keeps "when to use" text in `description`
     only; this repo's architecture guide also recommends a body-level
     `## When to Use` section. Resolved: keep the body section out when
     `description` already carries full trigger coverage (true for both
     skills here) — see the "Standards Conflict Note" in
     `skillify/SKILL.md`.
   - Anthropic's packaged-skill schema hard-caps `description` at 1024
     characters and only allows `name, description, license, compatibility,
     allowed-tools, metadata` in frontmatter. This repo's own convention
     allows a 1536-character combined cap and custom fields (`version`,
     `parent_skill`, `triggers`). Resolved: the **canonical repo SKILL.md**
     keeps the fuller orama-native frontmatter (other repo tooling reads
     it); the **packaged `.skill` file** carries a trimmed description and
     moves `version`/`parent_skill`/`triggers` under a `metadata:` key,
     built from a staged copy — see step 5.
   - `install_thin_skill_wrappers.py`'s `TARGET_ROOTS` only wrote to
     `~/.codex/skills` and `~/.agents/skills`, never `~/.claude/skills`.
     Resolved (operator-confirmed): add `~/.claude/skills` to the shared
     manifest permanently (so future full runs stay correct with no
     drift), but added a `--only <slug,...>` flag so any single run can be
     scoped instead of touching all ~30 registered skills at once.
4. **Add examples/ and eval/ where missing**, using
   `skill-folder-template.md`'s templates as the shape, but with content
   specific to the skill (not the generic placeholder text).
5. **Build a standalone `.skill` package from a staged copy, never the
   canonical file directly.** The canonical `SKILL.md` files legitimately
   use `../../references/*.md` links two levels up (shared repo-wide docs
   like `skill-architecture-guide.md`, `contribution-standards.md`). A
   packaged skill installed outside this repo can't resolve those. Stage a
   copy, bundle the referenced external files into the copy's own
   `references/`, rewrite the links to be one level away, fix the
   frontmatter to Anthropic's schema, then run
   `python -m scripts.package_skill <staged-copy> <output-dir>` from the
   skill-creator skill directory. Never edit the canonical repo file to
   match the packaged schema — the two have different, legitimate
   constraints.
6. **Run the scoped eval loop honestly.** Snapshot the pre-edit version via
   `git show HEAD:<path>` (don't rely on remembering to snapshot first).
   Spawn one with-skill and one old-version subagent per representative
   eval prompt, save transcripts under
   `<skill-name>-workspace/iteration-N/eval-N/{with_skill,old_skill}/outputs/`,
   and generate a static review with
   `eval-viewer/generate_review.py <workspace/iteration-N> --static <path>`
   (Cowork has no display, so always use `--static`, never the server
   mode). State plainly which tools were live versus simulated — this
   repo's `gbrain`, `mcp-oramasys`, and OpenClaw gateway are not reachable
   from every harness that might run these evals.
7. **Wire, then hand off what can't be reached directly.** Writing outside
   this repository (`~/.claude/skills`, `~/.cowork/skills`) is an
   explicit Ask First boundary in `skillify/SKILL.md` — confirm scope
   first. Some host paths may be protected from direct agent write access
   entirely (found in this pass: `~/.claude/skills` could not be mounted
   in Cowork); when that happens, hand the operator the exact tested
   command instead of silently skipping the step.

## This Pass's Audit Notes

```text
AUDIT: 2026-07-22 skillify upgrade added examples/, eval/checklist.md, eval/evals.json; added a "Standards Conflict Note" section; version 1.4.1 -> 1.5.0. Verification: 6Cs review, line count 168 (<=500 ceiling; new-skill 200 target doesn't strictly apply to an existing/exceptional file), scoped dogfood eval (iteration-1/eval-0, skillify-workspace).
AUDIT: 2026-07-22 oramasys-method upgrade added examples/, eval/checklist.md, eval/evals.json (with a sandbox-limitation note); version 1.2.0 -> 1.3.0. Verification: 6Cs review, line count 205 (<=500 ceiling), scoped dogfood eval (iteration-1/eval-0, oramasys-method-workspace).
AUDIT: 2026-07-22 install_thin_skill_wrappers.py extended: added ~/.claude/skills to TARGET_ROOTS (permanent, affects all registered skills on the next full run) and added --only <slugs> for scoped runs. Verification: syntax check, --dry-run, a real --install --only oramasys-method,skillify against a scratch HOME, and --verify --only oramasys-method,skillify — all passed. Real ~/.claude/skills on the operator's machine could not be mounted from this session (protected host location); the tested command was handed off instead of run directly.
AUDIT: 2026-07-22 packaged skillify.skill and oramasys-method.skill from staged copies with bundled cross-repo references and Anthropic-schema-compliant frontmatter (description <=1024 chars, custom fields moved under metadata:). Verification: scripts.package_skill validation passed for both.
AUDIT: 2026-07-22 INCIDENT + REMEDIATION — the prior pass's `~/.claude/skills`
  addition to install_thin_skill_wrappers.py's TARGET_ROOTS was later run for
  real (outside this session) and silently overwrote gstack's own bundled
  `skillify` skill at ~/.claude/skills/skillify/SKILL.md (an unrelated skill
  that happens to share the same name — gstack's codifies browser scrapes;
  this repo's builds/upgrades skills). Recovered by copying gstack's own
  source of truth (~/.claude/skills/gstack/skillify/SKILL.md, 1230 lines)
  back over the clobbered file — confirmed byte-identical after restore.
  Root cause: the prior pass checked this repo's own manifest for name
  collisions but never checked external suites that also write to a shared
  global namespace. Fixed: (1) removed ~/.claude/skills from
  install_thin_skill_wrappers.py's TARGET_ROOTS entirely — that script isn't
  the right owner of global Claude Code publishing, scripts/install-skills.sh
  (repo root) already was; (2) added skillify to install-skills.sh under the
  disambiguated slug `oramasys-skillify` (not `skillify`); (3) added a
  generic collision guard to install-skills.sh's sync_one() that refuses any
  sync whose target name already exists under gstack's own manifest
  (~/.claude/skills/gstack/<name>), so this class of bug can't recur for any
  future addition to that list, not just skillify; (4) documented the check
  in modular-skill-authoring.md's Clobber Guard section and skillify/SKILL.md's
  Non-Negotiables. Cross-referenced this repo's full ~30-skill
  install_thin_skill_wrappers.py manifest against gstack's ~30-skill roster:
  only `skillify` actually collided; `gstack` (this repo's own gstack
  integration sub-skill) is a second slug that would collide if ever added to
  a global-publish list — flagged explicitly, not currently in one.
  Verification: `bash scripts/install-skills.sh` run for real post-fix —
  synced oramasys-skillify cleanly, no refusal, no gstack files touched;
  manually confirmed ~/.claude/skills/skillify/SKILL.md still matches
  gstack's source post-run.
```

## Re-Verification Commands

```bash
git -C bin/orama-system/skills/skillify log --oneline -3 -- SKILL.md
git -C bin/orama-system/skills/oramasys-method log --oneline -3 -- SKILL.md
find bin/orama-system/skills/skillify bin/orama-system/skills/oramasys-method -maxdepth 2 -type d
python3 bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py --verify --only oramasys-method,skillify
```

## Extending This Loop To Another Skill

1. Copy this file's Procedure section as a checklist.
2. Point step 1-4 at the target skill instead.
3. If the target skill has no `../../references/` escapes, skip step 5's
   bundling — package directly from the canonical folder.
4. Append new `AUDIT:` lines here rather than starting a second log file —
   one home for this fact, per the repo's own usability standard.
