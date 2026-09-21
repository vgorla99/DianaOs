"""
Single authoritative skill-resolution facade.

A single, code-owned place that knows about two explicit classes of skill,
so an HTTP route (or any other caller) never has to own its own competing
dispatch table:

- MANAGED: skills defined in instance/config/skills/*.yaml, backed by
  SkillDefinition/SkillRegistry. Subject to core.agents.runtime.dispatch()'s
  permission/approval/runtime checks. This module never executes or grants
  access to a MANAGED skill - it only reports whether a given name IS one,
  so a caller can refuse it. Agents reach MANAGED skills exclusively
  through dispatch(), never through this module.
- LEGACY_COMPAT: skills identified only by an import-path string, for
  backward-compatible dispatch outside the managed framework (e.g. an
  existing HTTP endpoint you don't want to migrate yet). Not subject to
  SkillDefinition/approval policy - inventing allowed_roots/
  allowed_projects/approval_level for skills with real external side
  effects needs deliberate, explicit policy, not an automatic default.
  Being listed here does NOT make a skill reachable by an agent -
  core/agents/runtime.py never imports this module.

Any caller resolving a skill by name should own zero independent dispatch
data of its own - it should call into this module for every resolution
decision.
"""
from __future__ import annotations

from core.skills.registry import SkillRegistry

LEGACY_COMPAT: dict[str, str] = {
    # Example only - replace with your own legacy skill modules. Each key
    # is the skill name reachable via /skills/{name}/run; each value is
    # the Python import path to a module with a run() (or similarly
    # named) entry point. Brand/business-specific skills belong in your
    # own separate package, never hardcoded here.
    "example_legacy_skill": "skills.example.example_legacy_skill",
}

_managed_registry = SkillRegistry()
_managed_registry.load("instance/config/skills")

MANAGED_IDS: frozenset[str] = frozenset(
    s.id for s in _managed_registry.list(enabled_only=False)
)


class UnknownSkillError(Exception):
    """Raised when a name is neither a MANAGED nor a LEGACY_COMPAT skill."""


def is_managed(skill_name: str) -> bool:
    return skill_name in MANAGED_IDS


def is_legacy(skill_name: str) -> bool:
    return skill_name in LEGACY_COMPAT


def legacy_ids() -> list[str]:
    return list(LEGACY_COMPAT.keys())


def resolve_legacy_module_path(skill_name: str) -> str:
    """The one place that knows a LEGACY_COMPAT skill name's import path.
    Raises UnknownSkillError for anything not in LEGACY_COMPAT - including
    MANAGED skill ids, which must never be resolved through this path."""
    if skill_name not in LEGACY_COMPAT:
        raise UnknownSkillError(f"'{skill_name}' is not a LEGACY_COMPAT skill")
    return LEGACY_COMPAT[skill_name]
