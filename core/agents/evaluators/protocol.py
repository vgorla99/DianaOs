"""
Evaluator protocol. Interface only for most evaluator types - this
release implements schema-validation only. Human approval reuses the
existing approval gate (core/control_plane/approval.py) exposed through
this same interface, rather than a second mechanism.

Deliberately not implemented yet (interface exists for later): test-result,
rule-based (beyond the minimal path check folded into schema-validation),
LLM-reviewer, security-reviewer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class EvaluatorResult:
    passed: bool
    evaluator: str
    detail: str = ""


class Evaluator(Protocol):
    def evaluate(self, output: Any) -> EvaluatorResult: ...
