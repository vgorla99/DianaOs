"""
Minimal orchestrator entrypoint.

Dispatches a request to exactly one skill, through the approval/audit
layers above, demonstrating the routing mechanism end-to-end. This is not
a skill registry - see core/skills/registry.py for that.
"""
from __future__ import annotations

from typing import Any

from core.control_plane.approval import ApprovalLevel, check_approval
from core.control_plane.audit_log import record_action

# Proven route: briefing generation. It reads vault state and calls an LLM,
# and - as side effects of the skill itself, not of this router - writes a
# daily vault note and sends a Telegram message. Those side effects are why
# this is classified SAFE_LOCAL_WRITE (a local, reversible write) rather
# than READ, even though the router call itself doesn't write anything.
ROUTE_LEVEL = ApprovalLevel.SAFE_LOCAL_WRITE
ROUTE_NAME = "briefing"


async def dispatch_briefing(focus: str = "all", approved: bool = True) -> dict[str, Any]:
    """
    Route a request to skills.assistant.briefing.run through the approval
    and audit layers. SAFE_LOCAL_WRITE doesn't require explicit approval by
    default (only level 3+ does), so approved=True is the normal caller
    value here, not a bypass - check_approval() still runs on every call
    and would still block if ROUTE_LEVEL were ever raised to 3+.
    """
    check_approval(ROUTE_NAME, ROUTE_LEVEL, approved=approved)

    # not part of this minimal release - wire up your own skill module and
    # update this import.
    from skills.assistant.briefing import run as briefing_run  # type: ignore[import-not-found]

    try:
        result = await briefing_run(focus=focus)
        record_action(
            action=ROUTE_NAME,
            level=ROUTE_LEVEL,
            approved=True,
            path="skills.assistant.briefing.run",
            detail=f"focus={focus}",
        )
        return result
    except Exception as exc:
        record_action(
            action=ROUTE_NAME,
            level=ROUTE_LEVEL,
            approved=True,
            path="skills.assistant.briefing.run",
            detail=f"focus={focus} error={exc}",
        )
        raise
