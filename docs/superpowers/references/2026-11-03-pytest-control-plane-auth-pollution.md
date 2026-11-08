# Pytest Control-Plane Auth Pollution — Reference

> Rule: inside a pytest session, importing `orama_system.portal_server` silently turns
> control-plane auth **on** for the rest of that process. Every later auth-gated request
> returns `401`, and the failures land in test modules that have nothing to do with auth.

## Why this matters

`tests/conftest.py` deliberately starts each session unauthenticated so legacy tests can
call routes without bearer tokens. That intent is undone by an import-time side effect in
production code, so whether the suite passes depends on **which test module gets imported
first**. The symptoms are misleading — `assert 401 == 200`, `KeyError: 'privacy'`, or a
missing `receipt` key — and read as per-module bugs rather than one process-global flag.

Two practical consequences:

- A single file run passes while the same file fails inside the full suite (or the reverse).
- The failure set changes between environments, so "it passes on my machine" is expected.

## Mechanism

The whole chain is deterministic; each step was verified at the cited line.

1. `tests/conftest.py:17` sets `PYTHON_DOTENV_DISABLED=1`, then pops
   `ORAMA_CONTROL_PLANE_TOKEN*` and the LAN bind flags (`ORAMA_BIND_LAN`,
   `PT_BIND_LAN`, `PORTAL_BIND_LAN`) at lines 19-24.
2. `tests/conftest.py:29` installs the autouse fixture `_orama_insecure_dev_for_tests`,
   which sets `ORAMA_INSECURE_DEV=1` for every test.
3. `src/utils/control_plane_auth.py:237` (`auth_enforced`) therefore returns `False` —
   see the `insecure in ("1", "true", "yes")` branch at lines 242-243 — so requests pass.
4. During **full collection**, something re-sets the bind-LAN flags after step 1 emptied
   them. Measured at `pytest_collection_finish` with all 3522 items collected:
   `ORAMA_BIND_LAN=1`, `PT_BIND_LAN=1`, `PORTAL_BIND_LAN=0`. With only two modules
   collected, the same probe shows all three still unset.
5. `portal_server`'s own dotenv load is **not** the writer. python-dotenv 1.2.2 honours
   `PYTHON_DOTENV_DISABLED` (`dotenv/main.py:409-418`), and importing
   `orama_system.portal_server` with the flag set leaves `os.environ` unchanged. The
   writer is still unidentified: the flip was observed between collection of
   `tests/test_fleet_topology_real_schema_regression.py` and
   `tests/test_fork_main_repoint.py`, but importing
   `orama_system.display_fleet_status` alone does not reproduce it.
6. `auth_enforced()` therefore takes the `insecure == "1" and lan_bind_configured()`
   branch at lines 240-241 (`lan_bind_configured` is defined at line 337) and returns
   `True` for the whole run — the per-test fixture only sets `ORAMA_INSECURE_DEV=1`, it
   never clears the leaked bind flags.
7. From then on `_control_plane_auth_middleware` (`portal_server.py:336`) and the route
   guard at `portal_server.py:1658` reject requests with
   `401 {"detail": "Bearer authentication required"}`.

The trigger is a collection-time env leak, not any test's own behaviour: the failure
appears in whichever modules run after the leaking module gets imported.

## Proof

The flip is measured inside a real pytest session, not by importing modules by hand. A
throwaway plugin (kept outside the repo) prints the control-plane environment at
`pytest_collection_finish`:

```python
import os


def pytest_collection_finish(session):
    print("[PROBE] n_items:", len(session.items))
    print("[PROBE] bind flags:", [
        k for k in ("PT_BIND_LAN", "ORAMA_BIND_LAN", "PORTAL_BIND_LAN") if os.getenv(k)
    ])
    from utils.control_plane_auth import auth_enforced
    print("[PROBE] auth_enforced:", auth_enforced())
```

Run with `PYTHONPATH=/tmp python3 -m pytest --collect-only -q -p env_probe3`:

```text
two modules -> n_items: 68    bind flags: []                                   auth_enforced: True
full suite  -> n_items: 3522  bind flags: ['PT_BIND_LAN', 'ORAMA_BIND_LAN',
                                           'PORTAL_BIND_LAN']                  auth_enforced: True
```

`auth_enforced()` reads `True` at collection-finish in both runs only because
`ORAMA_INSECURE_DEV` is still unset there (the autouse fixture has not run yet). The row
that matters is the leaked bind flags: empty with two modules, set with the full suite.

A second plugin hooked on `pytest_collectstart` reports the boundary where they appear:

```text
[FLIP] between tests/test_fleet_topology_real_schema_regression.py
       and tests/test_fork_main_repoint.py
    -> {'PT_BIND_LAN': (None, '1'), 'ORAMA_BIND_LAN': (None, '1'),
        'PORTAL_BIND_LAN': (None, '0')}
```

Negative controls:

```bash
# with conftest's flag set, portal_server's own load_dotenv is a no-op
PYTHONPATH=src:. PYTHON_DOTENV_DISABLED=1 python3 -c \
  "import os, orama_system.portal_server; print([k for k in \
   ('PT_BIND_LAN','ORAMA_BIND_LAN','PORTAL_BIND_LAN') if os.getenv(k)])"
# -> []      (drop the flag and the same import sets all three -- the original misreading)

# the two neighbouring modules, in collection order, do not reproduce the 401s
python3 -m pytest tests/e1_part3_conformance/test_section_3_3_conformance.py \
                  tests/test_api_server.py -q
# -> 68 passed
```

Correction: an earlier revision claimed the `portal_server` import was the writer, based
on a probe that omitted `PYTHON_DOTENV_DISABLED`. That probe demonstrated a real
mechanism but not the one operating in the suite; the claim is withdrawn and the board
note carrying it was corrected the same day.

## Fix options (applied & verified in stack)

Reproduction is cheap once scoped to the leaking module plus a victim module:

```bash
python3 -m pytest tests/test_fleet_topology_real_schema_regression.py \
                  tests/test_api_server.py tests/test_local_workspace.py -q
# Before R1 + R2: 57 failed, 12 passed   (0.8 s)
# After R1 + R2:  69 passed, 0 failed    (0.79 s)
```

**R1 — enforce hermeticity in `tests/conftest.py` (applied).** The per-test autouse
fixture sets `ORAMA_INSECURE_DEV=1` but previously tolerated leaked bind flags, taking
the `insecure == "1" and lan_bind_configured()` branch. Added to that fixture:

```python
for _name in ("ORAMA_BIND_LAN", "PORTAL_BIND_LAN", "PT_BIND_LAN"):
    monkeypatch.delenv(_name, raising=False)
```

**R2 — repair `fake_urlopen` signature in `test_fleet_topology_real_schema_regression.py` (applied).**
`test_http_get_retries_next_token_on_401` and `test_http_get_returns_none_when_all_candidates_rejected`
mocked `urlopen` with `def fake_urlopen(req, timeout=2)`. When `peer_tls.urlopen_kwargs`
forwarded `context=<SSLContext>`, Python raised `TypeError: unexpected keyword argument 'context'`,
which was caught by `_http_get`'s general handler and returned `None`. Adding `**kwargs: Any`
to `fake_urlopen` resolved both tests, achieving 69/69 passed across all three modules.

**R3 — stop import-time env mutation in production code.** `portal_server.py:106-109` runs
`load_dotenv` at module import. Move it into an explicit `load_env()` called from the
`__main__` entry point and the app lifespan, so importing the server can never mutate a
caller's environment. Do this after R1 lands; R1 is the cheap unblock.

**R4 — make the leak loud instead of silent.** A session-start guard turns a 57-failure
cascade into one actionable failure naming the leaked variables:

```python
def pytest_collection_finish(session):
    leaked = [k for k in ("ORAMA_BIND_LAN", "PORTAL_BIND_LAN", "PT_BIND_LAN") if os.getenv(k)]
    assert not leaked, f"control-plane bind flags leaked during collection: {leaked}"
```

**R5 — identify the writer (open).** Still unknown; the flip is bracketed to
`tests/test_fleet_topology_real_schema_regression.py`. Re-run the `pytest_collectstart`
probe from `## Proof` with `--collect-only` on shrinking file sets to pin the exact import
before attempting R3.

**Not recommended:** teaching `auth_enforced()` about `PYTEST_CURRENT_TEST`. It would make
tests immune to arbitrary environment leaks and hide the production-relevant question of
why a server import mutates global state.

## Symptom map

| Symptom in the full run | Typical module | Why it looks unrelated |
| --- | --- | --- |
| `assert 401 == 200` | `tests/test_api_server.py` | HTTP-bridge behaviour test hits the middleware |
| `KeyError: 'privacy'`, missing `receipt` | `tests/test_local_workspace.py` | the error body simply lacks the asserted keys |
| `403`/`401` on launch or approve | swarm and portal job tests | those routes are operator-gated by design |

Measured instance: a full run with services stopped reported 150 failed / 3319 passed /
53 skipped, with 190 occurrences of `401` in the log. `tests/test_local_workspace.py`
passes alone (24 passed) but failed 23 times in that run. `tests/test_api_server.py`
passes alone (34) and with one neighbouring module (68) yet failed repeatedly in the full
run.

## Diagnosing a suspect failure

1. Re-run just the failing file. If it passes alone, suspect session state before the code.
2. Search the full-run log for `401` near the failure before assuming a logic bug.
3. Bisect the import order with `pytest <file-a> <file-b> -q` to find the poisoning module.
4. Confirm with the probe above; `auth_enforced()` flipping to `True` is conclusive.

## Fix options (owner decision — none applied here)

- Make the `.env` / `.env.local` load in `portal_server` honour `PYTHON_DOTENV_DISABLED`,
  or skip the `override=True` load when running under test. Fixes the cause.
- Have `conftest` re-assert the inert values in a fixture that runs after collection
  imports, not only at module import. Contains the damage, leaves the trap in place.
- Make `auth_enforced()` ignore `lan_bind_configured()` under an explicit test-mode flag.
  Narrowest, but adds a test-only branch to a security decision path.

Any of these is a security-semantic change on an auth path and needs its own targeted
tests plus review; it must not ride along with unrelated model-governance work.

## Boundaries

- This documents one mechanism and its evidence. It does **not** establish that all 150
  failures in that run share this cause; only the sampled clusters were tied to it.
- No source, test, config, or `.env` file was changed while establishing this.
- Nothing here is a qualification approval, freeze, evidence acceptance, or merge
  authorization.

## Provenance

- Author/actor: agent id `cline-gemini-3.8-sweep-20261103`, 2026-11-03.
- Board: GossipBus topic `MODEL-GOVERNANCE/GEMINI-3.8-FLASH-SWEEP`, note `38643f84` with
  paired pulse `76cc3967`; the announcement for this reference is the follow-up pair.
- Baseline check: the first failure reproduced on a clean tree with unrelated work
  stashed (1 failed, 35 passed, `assert 401 == 200`), so this is not a regression from
  the model-governance sweep.
