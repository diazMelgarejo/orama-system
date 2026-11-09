# Pytest Control-Plane Auth Pollution — Reference

> Current rule (2026-11-09): collection-time LAN-bind pollution previously enabled auth
> in unrelated tests. The autouse fixture now clears the bind flags before each test.
> Portal import was not established as the writer; that original attribution is withdrawn.

## Why this matters

`tests/conftest.py` provides per-test insecure-development defaults so legacy tests can
call routes without bearer tokens. Before the fixture repair, collection-time environment
pollution made results depend on **which test module got imported first**. The misleading
symptoms included `assert 401 == 200`, `KeyError: 'privacy'`, and a missing `receipt` key.
Tests may still explicitly enable LAN binding to exercise production authentication.

## Historical mechanism (before the fixture repair)

These observations describe the original failing snapshot; line numbers are historical.

1. `tests/conftest.py:17` sets `PYTHON_DOTENV_DISABLED=1`, then pops
   `ORAMA_CONTROL_PLANE_TOKEN` and the LAN bind flags (`ORAMA_BIND_LAN`,
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

The current autouse fixture also clears those three bind flags and
`ORAMA_CONTROL_PLANE_TOKEN` before each test. Neither session setup nor that fixture clears
`ORAMA_CONTROL_PLANE_TOKEN_LOCAL` or `ORAMA_CONTROL_PLANE_TOKEN_PEER`; no wildcard token
isolation is claimed.

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
which was caught by `_http_get`'s general handler and returned `None`. Accepting TLS kwargs
resolved both tests (69/69 across three modules). The follow-up regressions also assert
that every retry receives the configured SSL context, rather than merely accepting it.

**R3 — explicit dotenv disable handling (applied).** Portal loading now explicitly honours
`PYTHON_DOTENV_DISABLED`, including dependency versions that did not honour it themselves.
Regression tests verify both full requested paths and override order using isolated dotenv
fixtures. Moving production environment loading into a lifespan is not part of this repair.

**R4 — optional collection diagnostic (not applied).** A collection-finish probe can expose
leaked variables before the repaired fixture clears them; it is not a production auth rule:

```python
def pytest_collection_finish(session):
    leaked = [k for k in ("ORAMA_BIND_LAN", "PORTAL_BIND_LAN", "PT_BIND_LAN") if os.getenv(k)]
    assert not leaked, f"control-plane bind flags leaked during collection: {leaked}"
```

**R5 — identify the writer (open).** Still unknown; the flip is bracketed to
`tests/test_fleet_topology_real_schema_regression.py`. Re-run the `pytest_collectstart`
probe from `## Proof` with `--collect-only` on shrinking file sets to pin the exact import.

**Not recommended:** teaching `auth_enforced()` about `PYTEST_CURRENT_TEST`. It would make
tests immune to arbitrary environment leaks and hide the production-relevant question of
why collection changed global state.

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

## Boundaries

- This documents one mechanism and its evidence. It does **not** establish that all 150
  failures in that run share this cause; only the sampled clusters were tied to it.
- The original investigation changed no source, tests, config or `.env`; later applied
  repairs are explicitly identified above. Local dotenv files remain outside test inputs.
- Nothing here is a qualification approval, freeze, evidence acceptance, or merge
  authorization.

## Provenance

- Author/actor: agent id `cline-gemini-3.8-sweep-20261103`, 2026-11-03.
- Board: GossipBus topic `MODEL-GOVERNANCE/GEMINI-3.8-FLASH-SWEEP`, note `38643f84` with
  paired pulse `76cc3967`; the announcement for this reference is the follow-up pair.
- Baseline check: the first failure reproduced on a clean tree with unrelated work
  stashed (1 failed, 35 passed, `assert 401 == 200`), so this is not a regression from
  the model-governance sweep.
