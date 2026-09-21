"""
AgentRegistry.

Explicit load-by-path only - no directory-scan-and-import-Python magic.
A YAML file existing under instance/config/agents/ does nothing until
something explicitly calls registry.load() on that directory.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from core.agents.schema import AgentDefinition


class DuplicateAgentError(Exception):
    """Raised when two definitions share the same (id, version) at load time."""


class AgentValidationError(Exception):
    """Raised when a YAML file fails schema validation, with the field-level error attached."""


class AgentNotFoundError(Exception):
    pass


class AgentRegistry:
    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], AgentDefinition] = {}

    def load(self, directory: str) -> None:
        """Load and validate every *.yaml file directly under `directory`."""
        for path in sorted(Path(directory).glob("*.yaml")):
            with open(path, encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            try:
                definition = AgentDefinition.from_yaml_dict(raw)
            except ValidationError as exc:
                raise AgentValidationError(f"{path}: {exc}") from exc

            key = (definition.id, definition.version)
            if key in self._by_key:
                raise DuplicateAgentError(
                    f"Duplicate agent id+version {key} - already loaded from a prior file, found again in {path}"
                )
            self._by_key[key] = definition

    def get(self, id: str, version: str | None = None) -> AgentDefinition:
        """
        Returns the definition even if disabled=False - callers that need
        to DISPATCH an agent must separately check `.enabled` before
        proceeding (see core/agents/runtime.py). get() alone never implies
        "safe to run".
        """
        if version is not None:
            key = (id, version)
            if key not in self._by_key:
                raise AgentNotFoundError(f"No agent {id!r} version {version!r} loaded")
            return self._by_key[key]

        matches = [d for (aid, _v), d in self._by_key.items() if aid == id]
        if not matches:
            raise AgentNotFoundError(f"No agent {id!r} loaded (any version)")
        # highest version string wins when unspecified - simple lexical/semver-ish compare
        return sorted(matches, key=lambda d: d.version)[-1]

    def list(self, enabled_only: bool = True) -> list[AgentDefinition]:
        values = list(self._by_key.values())
        if enabled_only:
            values = [d for d in values if d.enabled]
        return values
