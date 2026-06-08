# 28 — agAIntra / againtra-platform v2 Requirements Alignment

> **Status:** CANONICAL — establishes that `oramasys/againtra-platform` (the v2 trading
> platform, formerly "agentra" — renamed to avoid copyright collision) MUST align its
> toolchain and runtime requirements with `perpetua-core` and the oramasys v2 standard.
> Added: 2026-06-06.

---

## 1 — Why this doc exists

The v1 playground (`diazMelgarejo/agentra-dingbot`) was bootstrapped quickly and made its
own toolchain choices. As we graduate to `oramasys/againtra-platform` (v2), those choices
must be harmonized with the rest of the orama stack. Drift here creates integration debt
that compounds every time a shared library (perpetua-core, orama-system) is updated.

This doc is the binding contract between the platform team (agAIntra) and the
oramasys v2 standards council.

---

## 2 — Why mypy is required

mypy is required in this codebase — not optional — for the following reasons:

| Reason | Detail |
|--------|--------|
| **Type safety at agentic speed** | The autoresearcher loop (doc 25) runs code continuously. Without static types, agentic edits accumulate subtle type bugs that only surface at runtime (inside live trading pipelines). |
| **LangGraph → MiniGraph migration safety** | Phase 2 swaps LangGraph for perpetua-core/MiniGraph. Typed state classes (`TradingState`, `PerpetuaState`) make the migration mechanical; untyped code makes it guesswork. |
| **orama v2 standard** | All `oramasys/*` repos run mypy clean. `againtra-platform` is a first-class orama v2 repo. |
| **Pydantic v2 + mypy synergy** | The platform uses Pydantic v2 throughout. Pydantic's mypy plugin (`pydantic.mypy`) turns runtime validation errors into compile-time errors — critical for the `TradingState` dataclass and agent return types. |

mypy is configured with `--ignore-missing-imports --explicit-package-bases --python-version 3.12`
in CI. The `--python-version 3.12` flag is **required** to avoid false errors from macOS
system Python 3.9's stdlib (which lacks `datetime.UTC`, `enum.StrEnum`, etc. — both added
in Python 3.11).

---

## 3 — Canonical requirements (oramasys v2 standard)

All `oramasys/*` repos, INCLUDING `againtra-platform`, must meet these requirements:

| Requirement | v2 Standard | Notes |
|-------------|-------------|-------|
| **Python version** | `>=3.12` | `perpetua-core` was `>=3.11`; v2 target is `3.12+`. All new code targets 3.12. |
| **Type checker** | mypy `>=1.11` | Clean with `--python-version 3.12`. Pydantic mypy plugin if using pydantic models. |
| **Linter** | ruff `>=0.8`, `target-version = "py312"` | UP035 (deprecated typing) fully resolved. E501 ignored. |
| **Test framework** | pytest `>=8.3`, pytest-asyncio `>=0.24` | `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "function"` |
| **Typing annotations** | Python 3.12 native (`list`, `dict`, `X \| None`, `datetime.UTC`) | No `typing.List`, `typing.Optional`, `typing.Union` — auto-fixed by ruff UP035 |
| **Pydantic** | v2 (`>=2.0`) | `@field_validator` not `@validator`; `model_config` not `class Config` |
| **Nested settings** | `Field(default_factory=lambda: XConfig())` | Static defaults (`XConfig()` as field default) capture env vars at import time — breaks `monkeypatch` in tests |

---

## 4 — Nested BaseSettings: the lambda factory pattern

**CRITICAL:** In Pydantic v2 BaseSettings, nested config classes MUST use
`Field(default_factory=lambda: XConfig())`, NOT `XConfig()` as a static default.

```python
# ❌ WRONG — XConfig() is evaluated at class-body time (module import)
#   monkeypatch.setenv + cache_clear will NOT affect already-constructed instances
class Settings(BaseSettings):
    ml: MLConfig = MLConfig()

# ✅ CORRECT — factory is called at each Settings() instantiation
#   monkeypatch.setenv("ML_ENABLED", "false") + get_settings.cache_clear() WORKS
class Settings(BaseSettings):
    ml: MLConfig = Field(default_factory=lambda: MLConfig())
```

**Why `lambda`?** Using `default_factory=MLConfig` directly causes a mypy type error
(`type[MLConfig]` ≠ `Callable[[], MLConfig]`). The lambda's return type is inferred
correctly by mypy as `() -> MLConfig`.

This pattern is required in all `oramasys/*` repos using Pydantic BaseSettings with
nested config blocks.

---

## 5 — Testing doctrine alignment

From doc 26 (TDD + Outsourced Review), plus the event loop lesson learned in `agentra-v1`:

| Rule | Why |
|------|-----|
| `asyncio_default_fixture_loop_scope = "function"` | Prevents `RuntimeError: Event loop is closed` when sync tests call `asyncio.run()` before async tests |
| No `asyncio.run()` inside async tests | Creates an independent loop; call the coroutine directly |
| `monkeypatch.setenv` + `get_settings.cache_clear()` before constructing any settings-dependent object | Ensures test isolation for env-var-driven config |
| `--python-version 3.12` flag for local mypy | Avoids false errors from macOS system Python 3.9 stdlib |

---

## 6 — Migration gate from v1 → v2 platform

Before the `oramasys/againtra-platform` v2 repo is bootstrapped, the playground
(`diazMelgarejo/agentra-dingbot`) must:

- [ ] **Gate 1 (CI green):** pytest 100% pass, ruff clean, mypy clean — all on Python 3.12
- [ ] **Gate 2 (LangGraph → MiniGraph):** `TradingState` ported to `PerpetuaState`; graph
      wiring swapped from `langgraph.graph.StateGraph` to `perpetua_core.graph.MiniGraph`
- [ ] **Gate 3 (Type coverage):** mypy reports no errors without `--ignore-missing-imports`
- [ ] **Gate 4 (Heartbeat):** daily autoresearcher pulse triggers from orama-system heartbeat
      without human intervention (doc 25 §3)

Merge to `oramasys/againtra-platform` only after Gate 2 passes in the playground.

---

## 7 — Cross-references

- `docs/v2/25-autoresearcher-doctrine-and-againtra-flagship.md` — mission + guardrails
- `docs/v2/26-tdd-and-outsourced-review-doctrine.md` — TDD + outsourced review
- `diazMelgarejo/agentra-dingbot` — v1 playground (active CI with these requirements)
- `oramasys/perpetua-core` — kernel that `againtra-platform` v2 will use (`requires-python = ">=3.11"`, moving to `3.12+`)
- `oramasys/againtra-platform` — REFERENCE-ONLY future scaffold; never push until Gate 2
