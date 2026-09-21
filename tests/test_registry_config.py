"""Tests for AgentRegistry/SkillRegistry.load() - both against this
repo's own real examples/ directory (proving the shipped examples are
themselves valid) and against deliberately invalid synthetic config."""
from __future__ import annotations

import pytest
import yaml

from core.agents.registry import AgentRegistry, AgentValidationError
from core.skills.registry import SkillRegistry, SkillValidationError


def test_shipped_example_agent_loads_cleanly():
    ar = AgentRegistry()
    ar.load("examples/instance.example/config/agents")
    agent = ar.get("chief_of_staff")
    assert agent.enabled is False  # ships disabled, matching the framework's own safety default


def test_shipped_example_skill_loads_cleanly():
    sr = SkillRegistry()
    sr.load("examples/instance.example/config/skills")
    skill = sr.get("example_skill")
    assert skill.enabled is False


def test_invalid_agent_config_is_rejected(tmp_path):
    bad = tmp_path / "bad_agent.yaml"
    # missing required fields (name, role, persona_prompt, approval_level)
    bad.write_text(yaml.safe_dump({"id": "broken-agent", "version": "0.1.0"}), encoding="utf-8")

    ar = AgentRegistry()
    with pytest.raises(AgentValidationError):
        ar.load(str(tmp_path))


def test_invalid_skill_config_is_rejected(tmp_path):
    bad = tmp_path / "bad_skill.yaml"
    # missing required fields (name, execution_type, implementation, approval_level)
    bad.write_text(yaml.safe_dump({"id": "broken-skill", "version": "0.1.0"}), encoding="utf-8")

    sr = SkillRegistry()
    with pytest.raises(SkillValidationError):
        sr.load(str(tmp_path))
