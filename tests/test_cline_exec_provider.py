"""Exercise Cline command arguments without invoking a provider."""

import json
import os
from pathlib import Path
import subprocess

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "bin/orama-system/skills/cline-openclaw-agent/scripts"


@pytest.mark.parametrize("provider,model,expected", [
    (None, None, "cline-pass/glm-5.3-flash"),
    ("cline-pass", None, "cline-pass/glm-5.3-flash"),
    ("openai", None, None),
    ("openai", "custom-model", "custom-model"),
])
@pytest.mark.parametrize("entrypoint", ["shell", "mcp"])
def test_provider_model_arguments(tmp_path: Path, provider: str | None, model: str | None,
                                  expected: str | None, entrypoint: str) -> None:
    """Only Cline Pass receives its default model; explicit models are preserved."""
    stub = tmp_path / "cline"
    stub.write_text('#!/usr/bin/env python3\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n')
    stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}"}
    if entrypoint == "shell":
        args = ["bash", str(SCRIPTS / "exec_cline.sh"), "test prompt"]
        if provider is not None:
            args += ["--provider", provider]
        if model is not None:
            args += ["--model", model]
        result = subprocess.run(args, env=env, text=True, capture_output=True, check=True, timeout=10)
        cli_args = json.loads(result.stdout)
    else:
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
            "name": "cline_exec", "arguments": {"prompt": "test prompt"}}}
        if provider is not None:
            request["params"]["arguments"]["provider"] = provider
        if model is not None:
            request["params"]["arguments"]["model"] = model
        process = subprocess.Popen(["node", str(SCRIPTS / "cline_mcp_server.mjs")], env=env,
                                   text=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        try:
            process.stdin.write(json.dumps(request) + "\n")
            process.stdin.flush()
            response = json.loads(process.stdout.readline())
            result = json.loads(response["result"]["content"][0]["text"])
            assert result["ok"], result
            cli_args = json.loads(result["stdout"])
        finally:
            process.terminate()
            process.communicate(timeout=10)
    assert cli_args[cli_args.index("-P") + 1] == (provider or "cline-pass")
    if expected is None:
        assert "-m" not in cli_args
    else:
        assert cli_args[cli_args.index("-m") + 1] == expected
