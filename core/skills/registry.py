"""SkillRegistry - same shape and rules as AgentRegistry."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from core.skills.models import SkillDefinition


class DuplicateSkillError(Exception):
    pass


class SkillValidationError(Exception):
    pass


class SkillNotFoundError(Exception):
    pass


class SkillRegistry:
    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], SkillDefinition] = {}

    def load(self, directory: str) -> None:
        for path in sorted(Path(directory).glob("*.yaml")):
            with open(path, encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            try:
                definition = SkillDefinition.from_yaml_dict(raw)
            except ValidationError as exc:
                raise SkillValidationError(f"{path}: {exc}") from exc

            key = (definition.id, definition.version)
            if key in self._by_key:
                raise DuplicateSkillError(
                    f"Duplicate skill id+version {key} - already loaded from a prior file, found again in {path}"
                )
            self._by_key[key] = definition

    def get(self, id: str, version: str | None = None) -> SkillDefinition:
        if version is not None:
            key = (id, version)
            if key not in self._by_key:
                raise SkillNotFoundError(f"No skill {id!r} version {version!r} loaded")
            return self._by_key[key]

        matches = [d for (sid, _v), d in self._by_key.items() if sid == id]
        if not matches:
            raise SkillNotFoundError(f"No skill {id!r} loaded (any version)")
        return sorted(matches, key=lambda d: d.version)[-1]

    def list(self, enabled_only: bool = True) -> list[SkillDefinition]:
        values = list(self._by_key.values())
        if enabled_only:
            values = [d for d in values if d.enabled]
        return values
