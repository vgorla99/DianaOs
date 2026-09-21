"""Tests proving AgentDefinition/SkillDefinition's allowlists default to
deny-all, never allow-all, when left empty. Synthetic agent/skill/project
names only."""
from __future__ import annotations

import pytest

from core.agents.registry import AgentRegistry
from core.agents.runtime import PermissionDeniedError, dispatch
from core.agents.schema import AgentDefinition
from core.skills.models import SkillDefinition
from core.skills.registry import SkillRegistry


def _agent(**overrides) -> AgentDefinition:
    base = dict(
        id="example-agent", version="0.1.0", name="Example Agent", role="example",
        persona_prompt="an example persona", enabled=True,
        allowed_skills=[], allowed_roots=[], allowed_projects=[], approval_level=0,
    )
    base.update(overrides)
    return AgentDefinition(**base)


def _skill(**overrides) -> SkillDefinition:
    base = dict(
        id="example-skill", version="0.1.0", name="Example Skill", execution_type="deterministic",
        implementation="does_not_matter_for_this_test", approval_level=0,
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


@pytest.mark.asyncio
async def test_empty_allowed_skills_denies_every_skill(isolated_audit_log):
    agent = _agent(allowed_skills=[])  # explicitly empty
    skill = _skill()
    ar, sr = _registries(agent, skill)

    with pytest.raises(PermissionDeniedError):
        await dispatch(ar, sr, agent.id, skill.id, approved=True)


@pytest.mark.asyncio
async def test_empty_allowed_roots_denies_a_skill_that_declares_a_root(isolated_audit_log, tmp_path):
    from core.filesystem import register_root

    agent = _agent(allowed_skills=["example-skill"], allowed_roots=[])  # explicitly empty
    skill = _skill(allowed_roots=["example_root"])
    ar, sr = _registries(agent, skill)

    # the root must be really registered for this to reach the permission
    # check that actually matters (an unknown root is denied for a
    # different reason).
    register_root("example_root", tmp_path / "example_root_dir")

    with pytest.raises(PermissionDeniedError):
        await dispatch(ar, sr, agent.id, skill.id, approved=True)


@pytest.mark.asyncio
async def test_empty_allowed_projects_denies_every_project(isolated_audit_log):
    agent = _agent(allowed_skills=["example-skill"], allowed_projects=[])  # explicitly empty
    skill = _skill(allowed_projects=[])
    ar, sr = _registries(agent, skill)

    with pytest.raises(PermissionDeniedError):
        await dispatch(ar, sr, agent.id, skill.id, project_id="example-project", approved=True)
