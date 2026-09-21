"""Tests for how a skill's `implementation` field resolves to real code.
Proves resolution only ever happens through the fixed IMPLEMENTATIONS
dict - never a YAML-controlled dynamic import."""
from __future__ import annotations

import inspect

import pytest

from core.agents.implementations import IMPLEMENTATIONS
from core.agents.registry import AgentRegistry
from core.agents.runtime import ImplementationNotFoundError, dispatch
from core.agents.schema import AgentDefinition
from core.skills.models import SkillDefinition
from core.skills.registry import SkillRegistry


def _agent(**overrides) -> AgentDefinition:
    base = dict(
        id="example-agent", version="0.1.0", name="Example Agent", role="example",
        persona_prompt="an example persona", enabled=True,
        allowed_skills=["example-skill"], allowed_roots=[], allowed_projects=[], approval_level=0,
    )
    base.update(overrides)
    return AgentDefinition(**base)


def _skill(**overrides) -> SkillDefinition:
    base = dict(
        id="example-skill", version="0.1.0", name="Example Skill", execution_type="deterministic",
        implementation="read_home_state", approval_level=0,
        allowed_roots=[], allowed_projects=[], enabled=True,
    )
    base.update(overrides)
    return SkillDefinition(**base)


def _registries(agent: AgentDefinition, skill: SkillDefinition) -> tuple[AgentRegistry, SkillRegistry]:
    ar = AgentRegistry()
    ar._by_key[(agent.id, agent.version)] = agent
    sr = SkillRegistry()
    sr._by_key[(skill.id, skill.version)] = skill
    return ar, sr


def test_known_implementation_id_is_present_in_the_fixed_dict():
    assert "read_home_state" in IMPLEMENTATIONS
    assert callable(IMPLEMENTATIONS["read_home_state"])


@pytest.mark.asyncio
async def test_known_implementation_id_resolves_and_executes(isolated_audit_log, isolated_config_root):
    # no home_state.yaml written - the real implementation returns {} on
    # ConfigNotFoundError, which is itself part of what's being proven:
    # a known ID resolves and runs, it doesn't require any private data.
    agent = _agent()
    skill = _skill(implementation="read_home_state")
    ar, sr = _registries(agent, skill)

    result = await dispatch(ar, sr, agent.id, skill.id, approved=True)
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_unknown_implementation_id_fails_closed(isolated_audit_log):
    agent = _agent()
    skill = _skill(implementation="this_id_is_not_in_the_fixed_dict")
    ar, sr = _registries(agent, skill)

    with pytest.raises(ImplementationNotFoundError):
        await dispatch(ar, sr, agent.id, skill.id, approved=True)


def test_no_dynamic_import_mechanism_in_runtime_dispatch():
    """Structural guarantee: a modified YAML file can only ever select
    among the exact functions already listed in IMPLEMENTATIONS - it can
    never name arbitrary code to run. Verified by absence of any dynamic
    import/attribute-lookup mechanism in the dispatch path's own source."""
    import core.agents.runtime as runtime_module

    source = inspect.getsource(runtime_module)
    # these are string literals checked for ABSENCE from runtime.py's source
    # below - nothing here calls eval()/exec(), this asserts they're never used.
    for forbidden in ("importlib", "__import__", "getattr(IMPLEMENTATIONS", "eval(", "exec("):
        assert forbidden not in source, f"found forbidden dynamic-dispatch pattern: {forbidden!r}"
