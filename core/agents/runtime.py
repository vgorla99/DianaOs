"""
Execution lifecycle.

Order: resolve agent -> resolve skill -> permission check (skill/project/
root, all of them) -> approval check -> validate input -> execute ->
validate output -> evaluator -> audit-log -> return.

Reuses core.control_plane's approval.py/audit_log.py directly - does not
reimplement either. Every denial (permission or approval) is audited
BEFORE the error is raised - a raise must never skip the audit trail.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from core.agents.evaluators.schema_validation import SchemaValidationError, validate_against_schema
from core.agents.implementations import IMPLEMENTATIONS
from core.agents.registry import AgentRegistry
from core.agents.schema import AgentDefinition
from core.control_plane.approval import ApprovalLevel, ApprovalRequiredError, check_approval
from core.control_plane.audit_log import record_action
from core.filesystem import list_roots
from core.skills.models import SkillDefinition
from core.skills.registry import SkillRegistry


class AgentDisabledError(Exception):
    pass


class SkillDisabledError(Exception):
    pass


class PermissionDeniedError(Exception):
    pass


class ImplementationNotFoundError(Exception):
    pass


def _new_run_id() -> str:
    return uuid.uuid4().hex[:16]


def _log(
    *, run_id: str, agent: Optional[AgentDefinition], skill: Optional[SkillDefinition],
    project_id: Optional[str], started_at: float, status: str, level: ApprovalLevel,
    approved: bool, detail: str = "", approval_result: Optional[str] = None,
    evaluator_result: Optional[str] = None,
) -> None:
    record_action(
        action=f"{agent.id if agent else '?'}:{skill.id if skill else '?'}",
        level=level,
        approved=approved,
        detail=detail,
        run_id=run_id,
        agent_id=agent.id if agent else None,
        agent_version=agent.version if agent else None,
        skill_id=skill.id if skill else None,
        skill_version=skill.version if skill else None,
        project_id=project_id,
        started_at=started_at,
        finished_at=time.time(),
        status=status,
        approval_level_required=int(level),
        approval_result=approval_result,
        errors=detail if status in ("error", "denied_permission", "denied_approval", "output_invalid") else None,
        evaluator_result=evaluator_result,
    )


async def dispatch(
    agent_registry: AgentRegistry,
    skill_registry: SkillRegistry,
    agent_id: str,
    skill_id: str,
    input_data: Optional[dict[str, Any]] = None,
    *,
    project_id: Optional[str] = None,
    approved: bool = False,
) -> dict[str, Any]:
    input_data = input_data or {}
    run_id = _new_run_id()
    started_at = time.time()

    # resolve agent
    agent = agent_registry.get(agent_id)
    if not agent.enabled:
        _log(run_id=run_id, agent=agent, skill=None, project_id=project_id, started_at=started_at,
             status="denied_agent_disabled", level=ApprovalLevel.READ, approved=False,
             detail=f"Agent '{agent_id}' is not enabled")
        raise AgentDisabledError(f"Agent '{agent_id}' is not enabled")

    # resolve skill
    skill = skill_registry.get(skill_id)
    if not skill.enabled:
        _log(run_id=run_id, agent=agent, skill=skill, project_id=project_id, started_at=started_at,
             status="denied_skill_disabled", level=ApprovalLevel.READ, approved=False,
             detail=f"Skill '{skill_id}' is not enabled")
        raise SkillDisabledError(f"Skill '{skill_id}' is not enabled")

    # permission check - unconditional membership only, never None-means-allow-all
    if skill_id not in agent.allowed_skills:
        _log(run_id=run_id, agent=agent, skill=skill, project_id=project_id, started_at=started_at,
             status="denied_permission", level=ApprovalLevel.READ, approved=False,
             detail=f"Agent '{agent_id}' may not invoke skill '{skill_id}'")
        raise PermissionDeniedError(f"Agent '{agent_id}' may not invoke skill '{skill_id}'")

    # project permission: agent AND skill must both explicitly allow it.
    # a project's approved_paths are NOT filesystem authority - this only
    # checks the project-allowlist concept, never implies root access, and
    # "unknown"/unmapped values are just ordinary strings here, never
    # special-cased into a grant.
    if project_id is not None:
        if project_id not in agent.allowed_projects or project_id not in skill.allowed_projects:
            _log(run_id=run_id, agent=agent, skill=skill, project_id=project_id, started_at=started_at,
                 status="denied_permission", level=ApprovalLevel.READ, approved=False,
                 detail=f"Project '{project_id}' not permitted for this agent/skill pair")
            raise PermissionDeniedError(f"Project '{project_id}' not permitted for this agent/skill pair")

    # root permission: every root the skill declares must be (a) a real
    # registered safe_path root and (b) explicitly allowed by the agent too.
    known_roots = set(list_roots())
    for root_id in skill.allowed_roots:
        if root_id not in known_roots:
            _log(run_id=run_id, agent=agent, skill=skill, project_id=project_id, started_at=started_at,
                 status="denied_permission", level=ApprovalLevel.READ, approved=False,
                 detail=f"Skill '{skill_id}' declares unknown root '{root_id}'")
            raise PermissionDeniedError(f"Skill '{skill_id}' declares unknown root '{root_id}'")
        if root_id not in agent.allowed_roots:
            _log(run_id=run_id, agent=agent, skill=skill, project_id=project_id, started_at=started_at,
                 status="denied_permission", level=ApprovalLevel.READ, approved=False,
                 detail=f"Agent '{agent_id}' is not permitted to use root '{root_id}'")
            raise PermissionDeniedError(f"Agent '{agent_id}' is not permitted to use root '{root_id}'")

    # approval check - ceiling is the higher of agent/skill declared levels,
    # capped by whatever check_approval() itself requires regardless
    required_level = ApprovalLevel(max(agent.approval_level, skill.approval_level))
    try:
        check_approval(f"{agent_id}:{skill_id}", required_level, approved=approved)
    except ApprovalRequiredError as exc:
        _log(run_id=run_id, agent=agent, skill=skill, project_id=project_id, started_at=started_at,
             status="denied_approval", level=required_level, approved=False,
             detail=str(exc), approval_result="denied")
        raise

    # validate input (skill's schema - the input belongs to the skill, not the agent)
    if skill.input_schema:
        try:
            validate_against_schema(input_data, skill.input_schema)
        except SchemaValidationError as exc:
            _log(run_id=run_id, agent=agent, skill=skill, project_id=project_id, started_at=started_at,
                 status="input_invalid", level=required_level, approved=True, detail=str(exc))
            raise

    # execute
    impl = IMPLEMENTATIONS.get(skill.implementation)
    if impl is None:
        _log(run_id=run_id, agent=agent, skill=skill, project_id=project_id, started_at=started_at,
             status="implementation_not_found", level=required_level, approved=True,
             detail=f"Unknown implementation id: {skill.implementation!r}")
        raise ImplementationNotFoundError(f"Unknown implementation id: {skill.implementation!r}")

    try:
        output = await impl(**input_data)
    except Exception as exc:
        _log(run_id=run_id, agent=agent, skill=skill, project_id=project_id, started_at=started_at,
             status="error", level=required_level, approved=True, detail=str(exc))
        raise

    # validate output + evaluator (same check, one implementation, not two copies)
    evaluator_result = "not_run"
    if skill.output_schema:
        try:
            validate_against_schema(output, skill.output_schema)
            evaluator_result = "passed"
        except SchemaValidationError as exc:
            _log(run_id=run_id, agent=agent, skill=skill, project_id=project_id, started_at=started_at,
                 status="output_invalid", level=required_level, approved=True, detail=str(exc),
                 evaluator_result="failed")
            raise

    _log(run_id=run_id, agent=agent, skill=skill, project_id=project_id, started_at=started_at,
         status="success", level=required_level, approved=True, approval_result="granted",
         evaluator_result=evaluator_result)
    return output
