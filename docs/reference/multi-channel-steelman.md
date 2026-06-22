# Multi-Channel Steelman — an orama execution pattern

> Version: 1.1.0.0 · Dogfooded 2026-06-02 from the gstack#1802 fix session.
> A concrete Mode-3 recipe: how to use heterogeneous external models as a real
> review panel instead of theater. Pairs with the 6 Directives and the 5-stage flow.

## When to use

A change is small but **high-stakes** (data-loss, security, irreversible), the
design has genuine tradeoffs, and you want the most *inevitable* solution — not
just a passing one. Single-model review (even self-review) anchors on one prior.
A panel of *different model families* surfaces the objection your lineage is blind to.

## The discipline (what makes it substance, not theater)

1. **Verify reachability before claiming dispatch.** Probe every channel with a
   real round-trip (a models list, a 1-token completion) *before* you say you
   asked it. Report dead channels as dead. (gstack#1802: Antigravity had no CLI,
   AgentRouter no key, Cursor no local dispatch — named as unreachable, not faked.)
2. **One brief, embedded design, sharp questions.** Give every reviewer the same
   self-contained brief with the *concrete proposal* and 3-4 pointed questions
   ("strongest objection?", "this knob — yes/no?", "more inevitable design?").
   Blank-prompt brainstorming wastes the panel.
3. **Heterogeneous families.** Diversity is the product. gstack#1802 panel:
   Gemini CLI, OpenAI Codex, OpenRouter (gpt-4o), local LM Studio qwen-27b.
   Same-family reviewers mostly agree with you and each other.
4. **Background + time-box.** Dispatch in parallel, `run_in_background`, `timeout`
   each. A slow local 27B that times out is a logged fact, not a blocker.
5. **Count the vote AND weigh the argument.** Convergence is signal; a lone
   dissent with a sound mechanism can still be right. gstack#1802: 3-1 for the
   marker, but the deciding factor was an *asymmetry argument* (missing marker
   fails safe) that no single voter fully articulated — synthesis is the orchestrator's job.
6. **Record the dissent in the artifact.** The PR/commit names the 3-1 split and
   why the minority lost. Intellectual honesty + future readers see the road not taken.

## The reusable channel probe (verified live on this machine)

```bash
# Each prints LIVE/DEAD without faking. Network probes need sandbox off.
curl -s --max-time 8 http://$WIN_IP:1234/v1/models            # LM Studio (LAN coder)
curl -s --max-time 10 https://openrouter.ai/api/v1/auth/key -H "Authorization: Bearer $OPENROUTER_API_KEY"
gemini -p "Reply: READY"                                       # Gemini CLI
codex --version                                                # Codex CLI
# dispatch pattern: build payload with python (safe quoting), background, timeout, write to /tmp
```
LAN IPs are DHCP — read `~/.openclaw/state/last_discovery.json` for the live `win`/`mac` endpoints first.

## The principle this fix taught: Fail-Closed Trust Boundary

> A routine that can recurse-delete must **prove** it owns the target, not assume it.
> If ownership can't be proven, do nothing. The cost of a false negative (an extra
> re-stage) must be trivially smaller than the cost of a false positive (deleting
> user data). Design the asymmetry in on purpose.

Ownership proof, strongest-to-cheapest, use all that apply:
- **Capability/marker** ("minted by us" — a token we wrote) — beats naming convention.
- **Structural containment** (direct child of our state root) — cheap first gate; canonicalize with realpath first to kill `..`/symlink escapes.
- **Catastrophe tripwire** (refuse if it contains `.git`) — last-line alarm; logs loud so tests notice.

This generalizes beyond gstack: any `rm -rf`, any bulk write, any "clean up the
temp dir" path. Add it to the [CIDF](../../bin/orama-system/SKILL.md) lineage of
"verify before the destructive act."

## Cross-refs
- **Dispatch engine (canonical):** [bin/orama-system/skills/mcp-orchestration/SKILL.md](../../bin/orama-system/skills/mcp-orchestration/SKILL.md) — this method is an *application* of mcp-orchestration's parallel multi-CLI dispatch (ai-cli-mcp, Gemini, Codex, OpenRouter, local). Use it for the wiring; this doc for the review discipline.
- **Review sibling:** [code-review `orchestration-dispatch`](../../bin/orama-system/skills/code-review/references/orchestration-dispatch.md) — the same fan-out applied to PR multi-lens review.
- Incident + root cause: [wiki/14-gbrain-checkpoint-rm-rf-bug.md](../wiki/14-gbrain-checkpoint-rm-rf-bug.md)
- Submission package: [reference/gstack-1802-submission-package.md](gstack-1802-submission-package.md)
- Upstream: garrytan/gstack#1802
