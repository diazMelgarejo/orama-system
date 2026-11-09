"""The peer gate must reject config and pin drift independently."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/review/verify_governance_parity.py"
spec = importlib.util.spec_from_file_location("governance_parity", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _repo(root, value, pin=None):
    """Create a minimal repository fixture with a governance digest."""
    (root / "config").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "config/model-governance.yml").write_text(f"model: {value}\n", encoding="utf-8")
    digest = hashlib.sha256(json.dumps({"model": value}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (root / "tests/test_model_governance.py").write_text(
        f"_PARITY_CONFIG_DIGEST = {pin or digest!r}\n", encoding="utf-8"
    )


def test_peer_gate_detects_config_and_digest_drift(tmp_path):
    """Verify peer gate detects config and digest drift."""
    local, peer = tmp_path / "local", tmp_path / "peer"
    _repo(local, "same")
    _repo(peer, "same")
    module.main(local, peer)
    (peer / "config/model-governance.yml").write_text("model: different\n", encoding="utf-8")
    with pytest.raises(ValueError, match="differ"):
        module.main(local, peer)
    (peer / "config/model-governance.yml").write_text("model: same\n", encoding="utf-8")
    (peer / "tests/test_model_governance.py").write_text("_PARITY_CONFIG_DIGEST = 'wrong'\n", encoding="utf-8")
    with pytest.raises(ValueError, match="differ"):
        module.main(local, peer)
