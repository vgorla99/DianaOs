"""
Approval-level model for the control plane.

This is a library other code can opt into - it is not automatically
enforced on every route/skill. The levels:

  0 - READ                     no side effects
  1 - SAFE_LOCAL_WRITE          local file/data changes, reversible
  2 - AUTHORIZED_CODE_CHANGE    code edits, local commits
  3 - EXTERNAL_HIGH_IMPACT      push, PR, deploy, dependency install
  4 - CRITICAL                  prod, credentials, destructive ops, history rewrite

Level 3+ actions must be explicitly approved before they proceed - the
default is always to refuse, never to assume yes.
"""
from __future__ import annotations

from enum import IntEnum
from functools import wraps
from typing import Callable, ParamSpec, TypeVar


class ApprovalLevel(IntEnum):
    READ = 0
    SAFE_LOCAL_WRITE = 1
    AUTHORIZED_CODE_CHANGE = 2
    EXTERNAL_HIGH_IMPACT = 3
    CRITICAL = 4


APPROVAL_REQUIRED_FROM = ApprovalLevel.EXTERNAL_HIGH_IMPACT


class ApprovalRequiredError(Exception):
    """Raised when an action at level >= APPROVAL_REQUIRED_FROM is attempted without approval."""

    def __init__(self, action: str, level: ApprovalLevel) -> None:
        self.action = action
        self.level = level
        super().__init__(
            f"Action '{action}' is level {level.name} ({int(level)}) and requires "
            "explicit approval before it can proceed. approved=True was not passed."
        )


def check_approval(action: str, level: ApprovalLevel, approved: bool = False) -> None:
    """
    Raise ApprovalRequiredError if `level` requires approval and `approved`
    is not True. This function never grants approval itself - callers must
    obtain approval (a user prompt, a config flag, an audited decision)
    through their own path before passing approved=True.
    """
    if level >= APPROVAL_REQUIRED_FROM and not approved:
        raise ApprovalRequiredError(action, level)


P = ParamSpec("P")
R = TypeVar("R")


def require_approval(
    level: ApprovalLevel, action: str | None = None
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator form. The wrapped function must accept an `approved: bool = False`
    keyword argument; check_approval() runs against it before the function executes.
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        action_name = action or fn.__name__

        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            approved = bool(kwargs.get("approved", False))
            check_approval(action_name, level, approved=approved)
            return fn(*args, **kwargs)

        return wrapper

    return decorator
