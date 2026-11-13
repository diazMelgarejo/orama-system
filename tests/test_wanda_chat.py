"""Wanda refuses to call W&B until the shell-sourced variables are present."""

import importlib.util
import os
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin/orama-system/skills/wanda-wandb/scripts/wanda_chat.py"


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
    class Message:
        content = "PING"

    class Choice:
        message = Message()

    class Response:
        choices = [Choice()]

    class Completions:
        @staticmethod
        def create(**_kwargs):
            return Response()

    class Chat:
        completions = Completions()

    class Client:
        def __init__(self, **_kwargs):
            self.chat = Chat()

    openai = types.ModuleType("openai")
    openai.APIError = type("APIError", (Exception,), {})
    openai.OpenAI = Client
    weave = types.ModuleType("weave")
    weave.init = lambda _project: None
    monkeypatch.setitem(sys.modules, "openai", openai)
    monkeypatch.setitem(sys.modules, "weave", weave)
    monkeypatch.setenv("DEEPSEEK_V4_FLASH_WANDB", "present")
    monkeypatch.setenv("DEEPSEEK_V4_FLASH_WANDB_PROJECT", "present")

    code = _load_wanda().main(["Reply with exactly PING"])

    assert code == 0
    assert capsys.readouterr().out.strip() == "PING"
