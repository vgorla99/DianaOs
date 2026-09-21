"""
SkillDefinition schema.

`implementation` is an IMPLEMENTATION ID (e.g. "read_home_state"), never a
Python import path or module reference. It resolves ONLY through a fixed,
code-owned IMPLEMENTATIONS dict (see core/agents/implementations.py) - no
importlib, no dynamic module resolution, no getattr-based lookup, no
directory auto-discovery. A modified YAML file must never be able to
execute arbitrary code by naming an arbitrary module path.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SkillDefinition(BaseModel):
    id: str
    version: str
    name: str
    execution_type: Literal["deterministic", "ai_reasoning", "hybrid"]
    implementation: str = Field(description="An implementation ID resolved via IMPLEMENTATIONS - never a Python import path")
    approval_level: int
    allowed_roots: list[str] = Field(default_factory=list)
    allowed_projects: list[str] = Field(default_factory=list)
    input_schema: dict | None = None
    output_schema: dict | None = None
    enabled: bool = False

    @classmethod
    def from_yaml_dict(cls, data: dict) -> "SkillDefinition":
        """Validate a dict loaded from an instance/config/skills/*.yaml file."""
        return cls(**data)
