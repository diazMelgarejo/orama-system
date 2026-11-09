"""Check both repositories' governance config and recorded digest together."""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

import yaml


def snapshot(root: Path) -> tuple[object, str, str]:
    """Read a repository governance configuration and its recorded digest."""
    config = yaml.safe_load((root / "config/model-governance.yml").read_text(encoding="utf-8"))
    digest = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    tree = ast.parse((root / "tests/test_model_governance.py").read_text(encoding="utf-8"))
    pins = [ast.literal_eval(node.value) for node in tree.body
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "_PARITY_CONFIG_DIGEST"
                for target in node.targets)]
    if len(pins) != 1 or not isinstance(pins[0], str):
        raise ValueError(f"invalid governance digest pin in {root}")
    return config, digest, pins[0]


def main(local: Path, peer: Path) -> None:
    """Compare the configurations and digest pins across both repositories."""
    local_config, local_digest, local_pin = snapshot(local)
    peer_config, peer_digest, peer_pin = snapshot(peer)
    if local_config != peer_config or local_digest != local_pin or peer_digest != peer_pin:
        raise ValueError("governance configs or digest pins differ across repositories")
    print(f"Governance config and digest match: {local_digest}")


if __name__ == "__main__":
    main(Path(__file__).resolve().parents[2], Path(sys.argv[1]))
