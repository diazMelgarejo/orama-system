# Hardware Model Routing — Part 2 Plan
**File:** `2026-04-26-hardware-model-routing-004-PART2-PLAN.md`
**Continues:** `2026-04-26-MERGED-hardware-model-routing-003-PLAN.md`
**Branch:** `main` (commit to `2026-04-24-001-orama-salvage` if re-opened as a branch)
**Status:** Pending — Phase 1–4 of the original plan shipped; this plan covers remaining gaps

---

## Context — What Was Finished in Part 1

| Original Phase | Status | Notes |
|---|---|---|
| Phase 1 — Policy YAML | ✅ Shipped | `config/model_hardware_policy.yml` in PT; `shared:` still empty (intentional, Q3) |
| Phase 2 — discover.py filter | ✅ Shipped | `filter_models_for_platform()` called before every openclaw.json/discovery.json write |
| Phase 3 — AlphaClawManager gate | ✅ Shipped | `validate_routing_affinity()` instance method at line 252 of `alphaclaw_manager.py` |
| Phase 4 — api_server.py API gate | ✅ Shipped | HTTP 400 `HARDWARE_MISMATCH` at line 169; warning log added for stub path |
| Phase 5 — Live config repair | ❌ Not done | Requires both machines online + `discover.py --status` run |
| Phase 6 — Docs / LESSONS | ✅ Shipped | `docs/MODEL_HARDWARE_MATRIX.md`, `docs/LESSONS.md`, `AGENT_RESUME.md` all updated |
| Registry schema (agents[]) | ✅ Fixed | All 7 stage agents now have `"affinity"` keys (commit b2ed93b) |

---

## Open Gap Inventory (4 items)

| # | Gap | File(s) | Impact |
|---|-----|---------|--------|
| G1 | `shared:` section in policy YAML is empty | `PT/config/model_hardware_policy.yml` | Cross-platform models unidentifiable |
| G2 | `PERPETUA_TOOLS_ROOT` not documented in `.env.example` | `orama-system/.env.example` | New devs silently get stub (no enforcement) |
| G3 | `autoresearch_agents` uses `device_affinity` key; `agents` uses `affinity` | `bin/config/agent_registry.json` | Schema inconsistency; routing code must normalize |
| G4 | Live `openclaw.json` has not been repaired on either machine | Runtime file | Wrong models still reachable until repaired |

---

## Phase 5 — Live Config Repair (Blocked: Both Machines Required)

**Prerequisite:** Mac and Windows both online with LM Studio running.

### Step 5.1 — Backup existing configs (both machines)

```bash
# Mac
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-$(date +%Y%m%d)
cp discovery.json discovery.json.bak-$(date +%Y%m%d) 2>/dev/null || true

# Windows (run in orama-system dir)
copy openclaw.json openclaw.json.bak
```

### Step 5.2 — Re-run discover.py with policy enforcement active

```bash
# Set env var first
export PERPETUA_TOOLS_ROOT=/path/to/perplexity-api/Perpetua-Tools

# Run discovery — this triggers filter_models_for_platform() before every write
python scripts/discover.py --all

# Verify: mac-only models absent from Windows output, windows-only absent from Mac
python scripts/hardware_policy_cli.py validate
```

### Step 5.3 — Populate `shared:` section in policy YAML

After running discovery on both machines, compare model lists:

```bash
# On Mac:
python scripts/discover.py --status | grep "model:" > /tmp/mac_models.txt

# On Windows:
python scripts/discover.py --status | grep "model:" > /tmp/win_models.txt

# Diff to find models present on BOTH:
comm -12 <(sort /tmp/mac_models.txt) <(sort /tmp/win_models.txt)
```

Add confirmed cross-platform models to `PT/config/model_hardware_policy.yml`:

```yaml
shared:
  - llama3.2:3b          # example — verify before adding
  - phi3.5:mini          # example — verify before adding
```

Closes **G1**.

---

## Phase 7 — Schema Normalization: `device_affinity` → `affinity`

The `autoresearch_agents` block uses `device_affinity` (string, e.g. `"win-rtx3080"`, `"mac"`).
The `agents` array uses `affinity` (string, e.g. `"win"`, `"mac"`).

### Step 7.1 — Decide canonical key name

Recommendation: adopt `affinity` everywhere. `device_affinity` was the original key before
the hardware policy work unified naming.

### Step 7.2 — Migrate `autoresearch_agents` entries

In `bin/config/agent_registry.json`, rename `device_affinity` → `affinity` and normalize values:

| Old value | New value |
|-----------|-----------|
| `"win-rtx3080"` | `"win"` |
| `"mac"` | `"mac"` (unchanged) |

### Step 7.3 — Update routing code that reads the key

Search for any code that reads `device_affinity` and update to use `affinity`:

```bash
grep -r "device_affinity" . --include="*.py" --include="*.js"
```

### Step 7.4 — Verify with existing tests

```bash
cd orama-system && python -m pytest scripts/tests/ -q
```

Closes **G3**.

---

## Phase 8 — `.env.example` Documentation

Add `PERPETUA_TOOLS_ROOT` to `orama-system/.env.example` so new devs know to set it:

```bash
# Path to Perpetua-Tools repo root (sibling directory by default).
# Set this if PT is not at ../perplexity-api/Perpetua-Tools
# PERPETUA_TOOLS_ROOT=/absolute/path/to/Perpetua-Tools
```

Also add to `PT/.env.example`:

```bash
# Set by orama-system to locate this repo for cross-repo imports.
# Not needed inside PT itself — used by orama api_server.py and discover.py
# PERPETUA_TOOLS_ROOT=/absolute/path/to/Perpetua-Tools
```

Closes **G2**.

---

## Verification Checklist (run before closing Part 2)

- [ ] `python -m pytest scripts/tests/ -q` → 16/16 pass in orama-system
- [ ] `python -m pytest tests/ -q` → 11/11 pass in Perpetua-Tools
- [ ] `python scripts/hardware_policy_cli.py validate` → no policy violations
- [ ] `grep -r "device_affinity" . --include="*.py"` → zero results (G3 resolved)
- [ ] `cat .env.example | grep PERPETUA_TOOLS_ROOT` → entry present (G2 resolved)
- [ ] `cat config/model_hardware_policy.yml | grep -A5 "shared:"` → at least 1 entry or explicit comment (G1 resolved)
- [ ] `openclaw.json` on both machines: Windows has no mac-only models, Mac has no windows-only models (G4 resolved)

---

## Commit Sequence for Part 2

```
feat(routing): Phase 7 — normalize device_affinity → affinity in agent_registry
feat(routing): Phase 8 — document PERPETUA_TOOLS_ROOT in .env.example
feat(routing): Phase 5 — live config repair (both machines verified)
docs(routing): populate shared models section in model_hardware_policy.yml
```

---

## Lessons to Record After Part 2

- Which models were confirmed cross-platform (for `shared:` section)
- Whether `device_affinity` normalization required changes to routing dispatch code
- Whether the `PERPETUA_TOOLS_ROOT` stub warning appeared during any agent run (validates the warning was useful)
