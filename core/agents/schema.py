"""
AgentDefinition schema.

This module is the single authoritative AgentDefinition namespace - no
parallel definition should exist elsewhere. `role` is a structural
discriminator only (e.g. "chief_of_staff", "researcher") - no code
anywhere may branch on `persona_prompt`'s contents, only on `role`.
`persona_prompt` holds the actual system-prompt/persona text; keeping it
separate from `role` means persona text can never accidentally become a
permission or routing decision.

A definition validating against this schema does not make it a production
agent - `enabled` still defaults to False.

Legacy content fields (chroma_collection, schedule, tasks, output_format,
temperature, max_tokens) are kept as optional fields rather than dropped,
so migrating an existing agent config to this schema never silently loses
content the runtime doesn't itself read or use.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AgentTask(BaseModel):
    id: str
    prompt: str


class AgentDefinition(BaseModel):
    # core fields
    id: str
    version: str
    name: str
    role: str = Field(description="Structural discriminator ONLY - never branched on persona_prompt's contents")
    persona_prompt: str = Field(description="System-prompt/persona text - display/behavior only, never used for permission or routing logic")
    enabled: bool = False
    allowed_skills: list[str] = Field(default_factory=list)
    allowed_roots: list[str] = Field(default_factory=list)
    allowed_projects: list[str] = Field(default_factory=list)
    approval_level: int

    # Legacy content fields (see module docstring) - not read by the
    # registry/runtime.
    chroma_collection: str | None = None
    schedule: str | None = Field(default=None, description="Cron expression, if this agent runs on a schedule")
    tasks: list[AgentTask] = Field(default_factory=list)
    output_format: Literal["json", "text", "markdown"] = "text"
    temperature: float = 0.7
    max_tokens: int = 2000

    @classmethod
    def from_yaml_dict(cls, data: dict) -> "AgentDefinition":
        """Validate a dict loaded from an instance/config/agents/*.yaml file."""
        return cls(**data)
