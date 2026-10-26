#!/usr/bin/env python3
"""
test_multi_agent.py
===================
Test suite for the ultrathink multi-agent package structure.
Run: pytest tests/test_multi_agent.py -v
"""
import json
import pytest
from pathlib import Path

ROOT   = Path(__file__).parent.parent
MULTI  = ROOT / "bin"


def _read_json_file(path: Path):
    """Parse a JSON file, following a git symlink checked out as a plain-text stub.

    Without symlink privilege (Windows, core.symlinks=false) git writes a symlink
    as a regular file whose content is the relative link target.
    """
    if path.is_file() and not path.is_symlink():
        raw = path.read_text(encoding="utf-8").strip()
        if raw and not raw.startswith(("{", "[")) and "\n" not in raw:
            path = (path.parent / raw).resolve()
    return json.loads(path.read_text(encoding="utf-8"))
AGENTS = ["orchestrator", "context", "architect", "refiner", "executor", "verifier", "crystallizer"]
SKILL_NAMES = {
    "orchestrator": "agent.md",
    "context":      "agent.md",
    "architect":    "agent.md",
    "refiner":      "agent.md",
    "executor":     "agent.md",
    "verifier":     "agent.md",
    "crystallizer": "agent.md",
}
QWEN_PRIORITY_MODEL = "qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2"


class TestAgentStructure:
    """Tests and helpers: TestAgentStructure."""
    @pytest.mark.parametrize("agent", AGENTS)
    def test_agent_directory_exists(self, agent):
        """Check: agent directory exists."""
        assert (MULTI / "agents" / agent).is_dir()

    @pytest.mark.parametrize("agent", AGENTS)
    def test_agent_skill_md_exists(self, agent):
        """Check: agent skill md exists."""
        skill_file = SKILL_NAMES[agent]
        path = MULTI / "agents" / agent / skill_file
        assert path.exists(), f"Missing SKILL.md for {agent}: {skill_file}"

    @pytest.mark.parametrize("agent", AGENTS)
    def test_agent_skill_has_frontmatter(self, agent):
        """Check: agent skill has frontmatter."""
        skill_file = SKILL_NAMES[agent]
        content = (MULTI / "agents" / agent / skill_file).read_text(encoding="utf-8")
        assert content.startswith("---"), f"{agent} SKILL.md must start with ---"
        assert "version:" in content
        assert "license: Apache 2.0" in content

    @pytest.mark.parametrize("agent", AGENTS)
    def test_agent_has_readme(self, agent):
        """Check: agent has readme."""
        assert (MULTI / "agents" / agent / "README.md").exists()

    @pytest.mark.parametrize("agent", AGENTS)
    def test_agent_has_tools_py(self, agent):
        """Check: agent has tools py."""
        tools_map = {
            "orchestrator": "orchestrator_logic.py",
            "context":      "context_tools.py",
            "architect":    "architecture_tools.py",
            "refiner":      "refinement_tools.py",
            "executor":     "execution_tools.py",
            "verifier":     "verification_tools.py",
            "crystallizer": "documentation_tools.py",
        }
        assert (MULTI / "agents" / agent / tools_map[agent]).exists()


class TestSharedUtilities:
    """Tests and helpers: TestSharedUtilities."""
    def test_oramasys_core_exists(self):
        """Check: oramasys core exists."""
        assert (MULTI / "shared" / "oramasys_core.py").exists()

    def test_legacy_ultrathink_core_wrapper_exists(self):
        """Check: legacy ultrathink core wrapper exists."""
        assert (MULTI / "shared" / "ultrathink_core.py").exists()  # back-compat shim retained until v2.0

    def test_state_manager_exists(self):
        """Check: state manager exists."""
        assert (MULTI / "shared" / "state_manager.py").exists()

    def test_message_bus_exists(self):
        """Check: message bus exists."""
        assert (MULTI / "shared" / "message_bus.py").exists()

    def test_core_has_stage_enum(self):
        """Check: core has stage enum."""
        content = (MULTI / "shared" / "oramasys_core.py").read_text(encoding="utf-8")
        assert "class Stage" in content
        assert "context_immersion" in content

    def test_core_has_task_state(self):
        """Check: core has task state."""
        content = (MULTI / "shared" / "oramasys_core.py").read_text(encoding="utf-8")
        assert "class TaskState" in content
        assert "elegance_score" in content


class TestConfig:
    """Tests and helpers: TestConfig."""
    def test_agent_registry_valid_json(self):
        """Check: agent registry valid json."""
        path = MULTI / "config" / "agent_registry.json"
        assert path.exists()
        data = _read_json_file(path)
        assert "agents" in data
        assert len(data["agents"]) == 7

    def test_all_agents_in_registry(self):
        """Check: all agents in registry."""
        data = _read_json_file(MULTI / "config" / "agent_registry.json")
        ids = [a["id"] for a in data["agents"]]
        for agent in ["orchestrator", "context-agent", "architect-agent",
                      "refiner-agent", "executor-agent", "verifier-agent", "crystallizer-agent"]:
            assert agent in ids, f"{agent} missing from registry"

    def test_qwen_priority_subagent_registered(self):
        """Check: qwen priority subagent registered."""
        data = _read_json_file(MULTI / "config" / "agent_registry.json")
        openclaw_agents = data["openclaw_agents"]

        assert openclaw_agents["coder"]["model"] == QWEN_PRIORITY_MODEL
        assert openclaw_agents["priority-subagent"]["model"] == QWEN_PRIORITY_MODEL
        assert openclaw_agents["priority-subagent"]["provider"] == "lmstudio-win"
        assert openclaw_agents["priority-subagent"]["soul"] == openclaw_agents["coder"]["soul"]

    def test_routing_rules_valid_json(self):
        """Check: routing rules valid json."""
        path = MULTI / "config" / "routing_rules.json"
        assert path.exists()
        data = _read_json_file(path)
        assert "rules" in data
        assert len(data["rules"]) > 5

    def test_mcp_servers_exist(self):
        """Check: mcp servers exist."""
        assert (MULTI / "mcp_servers" / "oramasys_orchestration_server.py").exists()
        assert (MULTI / "mcp_servers" / "ultrathink_orchestration_server.py").exists()
        assert (MULTI / "mcp_servers" / "agent_communication_server.py").exists()
