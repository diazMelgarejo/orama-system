"""The W&B launcher's parts: the sibling package is found however the launcher is started, and a test
patch aimed at a moved name can not silently stop applying.

The subprocess cases stop at the missing-key refusal or earlier, so none can start Cline or send a request.
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from cline_wandb_fixtures import SCRIPT, launcher, part

pytestmark = pytest.mark.unit

SKILL = SCRIPT.parents[1]
PACKAGE = SCRIPT.parent / "cline_wandb_launcher"
PROBE = textwrap.dedent("""\
    import importlib.util, json, sys
    if sys.argv[2] == "decoy-first":
        import cline_wandb_launcher  # the decoy on PYTHONPATH, imported before the launcher is loaded
    before = list(sys.path)
    spec = importlib.util.spec_from_file_location("probe_launcher", sys.argv[1])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    print(json.dumps({"path_unchanged": sys.path == before,
                      "parts": list(sys.modules["cline_wandb_launcher"].__path__),
                      "refusal": module.launcher_boundary_problem(1, 0)}))
    """)


def _launcher_path(tmp_path: Path, how: str) -> Path:
    """The launcher as a caller would name it: directly, or through a symlink."""
    if how == "linked-skill":
        (tmp_path / "linked").symlink_to(SKILL, target_is_directory=True)
        return tmp_path / "linked" / "scripts" / SCRIPT.name
    if how == "linked-file":
        (tmp_path / "linked.py").symlink_to(SCRIPT)
        return tmp_path / "linked.py"
    return SCRIPT


def _decoy_env(tmp_path: Path) -> dict[str, str]:
    """An environment whose PYTHONPATH offers a package of the same name that must never be used."""
    decoy = tmp_path / "decoy" / "cline_wandb_launcher"
    decoy.mkdir(parents=True)
    (decoy / "__init__.py").write_text("")
    (decoy / "defaults.py").write_text("raise AssertionError('the decoy package was imported')\n")
    return {"PATH": str(tmp_path), "HOME": str(tmp_path), "PYTHONPATH": str(decoy.parent),
            "PYTHONDONTWRITEBYTECODE": "1"}


@pytest.mark.parametrize("order", ["launcher-first", "decoy-first"])
@pytest.mark.parametrize("how", ["direct", "linked-skill", "linked-file"])
def test_loading_by_path_binds_the_real_sibling_package_and_leaves_sys_path_alone(
    tmp_path: Path, how: str, order: str,
) -> None:
    done = subprocess.run(
        [sys.executable, "-c", PROBE, str(_launcher_path(tmp_path, how)), order],
        cwd=tmp_path, env=_decoy_env(tmp_path), capture_output=True, text=True, timeout=30, check=False,
    )
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == {
        "path_unchanged": True, "parts": [str(PACKAGE)], "refusal": "invalid-launcher-bounds",
    }


@pytest.mark.parametrize("how", ["direct", "linked-skill", "linked-file"])
def test_running_as_a_script_from_another_directory_finds_its_parts(tmp_path: Path, how: str) -> None:
    argv = [sys.executable, str(_launcher_path(tmp_path, how)),
            "--max-requests", "1", "--max-total-output", "1", "--", "task"]
    done = subprocess.run(argv, cwd=tmp_path, env=_decoy_env(tmp_path), capture_output=True, text=True,
                          timeout=30, check=False)
    assert done.returncode == 1, done.stderr
    assert done.stderr.startswith(f"ERROR: {launcher.KEYVAR} is missing or empty"), done.stderr


@pytest.mark.parametrize("name", [
    "MAX_RESPONSE_BYTES", "_UPSTREAM_OPENER", "TERMINATE_GRACE_S", "signal_group", "signal_pid",
    "descendants", "terminate_group", "terminate_proc", "forward_signals",
])
def test_a_patch_aimed_at_a_moved_name_on_the_launcher_fails_loudly(
    monkeypatch: pytest.MonkeyPatch, name: str,
) -> None:
    """The launcher does not re-export these, so a stale patch raises instead of changing nothing."""
    with pytest.raises(AttributeError):
        monkeypatch.setattr(launcher, name, None)


def _forbid_real_signals(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object) -> None:
        pytest.fail(f"a patched test reached a real signal call: {args}")

    monkeypatch.setattr(part("process_tree").os, "kill", forbidden)
    monkeypatch.setattr(part("process_tree").os, "killpg", forbidden)


def test_the_proxy_stops_the_child_through_the_process_tree_patch_point(monkeypatch: pytest.MonkeyPatch) -> None:
    _forbid_real_signals(monkeypatch)
    stopped: list[tuple[object, int | None]] = []
    monkeypatch.setattr(part("process_tree"), "terminate_proc", lambda proc, group=None: stopped.append((proc, group)))
    proxy = launcher.AccountingProxyServer(
        (launcher.LOOPBACK_HOST, 0), launcher.AccountingProxyHandler, 1, 1, session_token="t",
    )
    child = object()
    try:
        proxy.set_child_proc(child, 4242)
        proxy.terminate_child()
    finally:
        proxy.server_close()
    assert stopped == [(child, 4242)]


def test_signal_relay_reaches_processes_only_through_the_process_tree_patch_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_real_signals(monkeypatch)
    relay, tree = part("signal_relay"), part("process_tree")
    sent: list[tuple[str, int, int]] = []
    handlers: dict = {}
    monkeypatch.setattr(relay.signal, "signal", lambda signum, handler: handlers.setdefault(signum, handler))
    monkeypatch.setattr(tree, "descendants", lambda root: {root + 1})
    monkeypatch.setattr(tree, "signal_group", lambda group, signum: sent.append(("group", group, signum)))
    monkeypatch.setattr(tree, "signal_pid", lambda pid, signum: sent.append(("pid", pid, signum)))
    received: list[int] = []
    relay.forward_signals(4242, received, set())
    term, kill = relay.signal.SIGTERM, relay.signal.SIGKILL
    handlers[term](term, None)
    handlers[term](term, None)
    assert sent == [("group", 4242, term), ("group", 4242, kill), ("pid", 4243, kill)]
    assert received == [term, term]
