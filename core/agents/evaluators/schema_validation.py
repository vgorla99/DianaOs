"""
Schema-validation evaluator - the one real evaluator implementation in
this release.

Minimal, dependency-free JSON-Schema-subset checker: `type: object` and
`required: [...]` only. No `jsonschema` dependency was added for this -
a lightweight, explicit implementation covers a common real need. If you
need real JSON Schema (oneOf/anyOf/pattern/etc.), swap this for the
`jsonschema` package.

Shared by core/agents/runtime.py's own output-validation step AND by this
Evaluator - one implementation, not two copies.
"""
from __future__ import annotations

from typing import Any

from core.agents.evaluators.protocol import EvaluatorResult


class SchemaValidationError(Exception):
    pass


def validate_against_schema(data: Any, schema: dict) -> None:
    """Raises SchemaValidationError on failure. No return value on success."""
    if schema.get("type") == "object" and not isinstance(data, dict):
        raise SchemaValidationError(f"Expected an object, got {type(data).__name__}")

    required = schema.get("required", [])
    if required:
        if not isinstance(data, dict):
            raise SchemaValidationError(f"Expected an object with required keys {required}, got {type(data).__name__}")
        missing = [k for k in required if k not in data]
        if missing:
            raise SchemaValidationError(f"Missing required key(s): {missing}")


class SchemaValidationEvaluator:
    def __init__(self, schema: dict) -> None:
        self._schema = schema

    def evaluate(self, output: Any) -> EvaluatorResult:
        try:
            validate_against_schema(output, self._schema)
            return EvaluatorResult(passed=True, evaluator="schema_validation")
        except SchemaValidationError as exc:
            return EvaluatorResult(passed=False, evaluator="schema_validation", detail=str(exc))
