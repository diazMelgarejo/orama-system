"""Wanda refuses to call W&B until the shell-sourced variables are present."""

import importlib.util
import os
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin/orama-system/skills/wanda-wandb/scripts/wanda_chat.py"

DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4.1-Flash-1017"
V41_FLASH = "deepseek-ai/DeepSeek-V4.1-Flash"
V4_FLASH_0731 = "deepseek-ai/DeepSeek-V4-Flash-0731"


def test_wanda_chat_requires_sourced_env() -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("DEEPSEEK_V4_FLASH_WANDB")}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "Reply with exactly PING"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "shell-sourced" in proc.stderr
    assert "DEEPSEEK_V4_FLASH_WANDB" not in proc.stdout


def _load_wanda():
    spec = importlib.util.spec_from_file_location("wanda_chat", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _install_client(monkeypatch, create):
    openai = types.ModuleType("openai")
    openai.APIError = type("APIError", (Exception,), {})
    openai.OpenAI = lambda **_kwargs: types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create))
    )
    weave = types.ModuleType("weave")
    weave.init = lambda _project: None
    monkeypatch.setitem(sys.modules, "openai", openai)
    monkeypatch.setitem(sys.modules, "weave", weave)
    monkeypatch.setenv("DEEPSEEK_V4_FLASH_WANDB", "present")
    monkeypatch.setenv("DEEPSEEK_V4_FLASH_WANDB_PROJECT", "present")


def test_wanda_chat_reports_completion_failure(monkeypatch) -> None:
    class APIError(Exception):
        status_code = 401

    class Completions:
        @staticmethod
        def create(**_kwargs):
            raise APIError("secret-request")

    class Chat:
        completions = Completions()

    class Client:
        def __init__(self, **_kwargs):
            self.chat = Chat()

    openai = types.ModuleType("openai")
    openai.APIError = APIError
    openai.OpenAI = Client
    weave = types.ModuleType("weave")
    weave.init = lambda _project: None
    monkeypatch.setitem(sys.modules, "openai", openai)
    monkeypatch.setitem(sys.modules, "weave", weave)
    monkeypatch.setenv("DEEPSEEK_V4_FLASH_WANDB", "present")
    monkeypatch.setenv("DEEPSEEK_V4_FLASH_WANDB_PROJECT", "present")

    code = _load_wanda().main(["Reply with exactly PING"])

    assert code == 1


def test_wanda_chat_prints_assistant_text(monkeypatch, capsys) -> None:
    captured: dict = {}

    class Message:
        content = "PING"

    class Choice:
        message = Message()
        finish_reason = "stop"

    class Response:
        choices = [Choice()]

    def create(**kwargs):
        captured.update(kwargs)
        return Response()

    _install_client(monkeypatch, create)
    code = _load_wanda().main(["Reply with exactly PING"])

    assert code == 0
    assert capsys.readouterr().out.strip() == "PING"
    assert captured["reasoning_effort"] == "high"
    assert captured["model"] == DEFAULT_MODEL


def test_unknown_model_without_effort_exits_2(monkeypatch) -> None:
    called = {"n": 0}

    def create(**_kwargs):
        called["n"] += 1
        raise AssertionError("create must not be called")

    _install_client(monkeypatch, create)
    code = _load_wanda().main(["ping", "--model", "vendor/unknown-model"])

    assert code == 2
    assert called["n"] == 0


def test_unknown_model_with_effort_low_sends_low(monkeypatch) -> None:
    captured: dict = {}

    class Message:
        content = "ok"

    class Choice:
        message = Message()
        finish_reason = "stop"

    def create(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(choices=[Choice()])

    _install_client(monkeypatch, create)
    code = _load_wanda().main(["ping", "--model", "vendor/unknown-model", "--effort", "low"])

    assert code == 0
    assert captured["reasoning_effort"] == "low"


def test_v41_medium_effort_exits_2(monkeypatch) -> None:
    called = {"n": 0}

    def create(**_kwargs):
        called["n"] += 1
        raise AssertionError("create must not be called")

    _install_client(monkeypatch, create)
    wanda = _load_wanda()
    for model in (DEFAULT_MODEL, V41_FLASH):
        called["n"] = 0
        code = wanda.main(["ping", "--model", model, "--effort", "medium"])
        assert code == 2
        assert called["n"] == 0


def test_v4_flash_0731_default_sends_medium(monkeypatch) -> None:
    captured: dict = {}

    class Message:
        content = "ok"

    class Choice:
        message = Message()
        finish_reason = "stop"

    def create(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(choices=[Choice()])

    _install_client(monkeypatch, create)
    code = _load_wanda().main(["ping", "--model", V4_FLASH_0731])

    assert code == 0
    assert captured["reasoning_effort"] == "medium"


def test_length_truncation_returns_3(monkeypatch, capsys) -> None:
    class Message:
        content = "partial answer"

    class Choice:
        message = Message()
        finish_reason = "length"

    def create(**_kwargs):
        return types.SimpleNamespace(choices=[Choice()])

    _install_client(monkeypatch, create)
    code = _load_wanda().main(["ping"])
    out = capsys.readouterr().out

    assert code == 3
    assert "INCOMPLETE: finish_reason=length" in out
    assert "partial answer" in out


def test_empty_choices_returns_1(monkeypatch, capsys) -> None:
    def create(**_kwargs):
        return types.SimpleNamespace(choices=[])

    _install_client(monkeypatch, create)
    code = _load_wanda().main(["ping"])
    err = capsys.readouterr().err

    assert code == 1
    assert err.strip()


def test_xhigh_refused(monkeypatch) -> None:
    called = {"n": 0}

    def create(**_kwargs):
        called["n"] += 1
        raise AssertionError("create must not be called")

    _install_client(monkeypatch, create)
    wanda = _load_wanda()
    for argv in (
        ["ping", "--effort", "xhigh"],
        ["ping", "--effort", "max"],
        ["ping", "--model", "vendor/unknown-model", "--effort", "xhigh"],
    ):
        called["n"] = 0
        assert wanda.main(argv) == 2
        assert called["n"] == 0
