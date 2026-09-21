"""
Example implementation functions for a Chief-of-Staff-style agent.

These are the ONLY functions resolvable via the fixed IMPLEMENTATIONS dict
below - each SkillDefinition.implementation string maps to exactly one
entry here, by explicit code, never importlib/dynamic resolution.

project_status / git_status: thin wrappers intended to call your own
project-registry routes (see README.md - not part of this release).
read_home_state: fully self-contained, reads instance/config/home_state.yaml.

create_briefing: an example of a skill that calls an LLM and writes its
own output through safe_path, using the "briefing_output" root
(instance/runtime/briefings/, gitignored) - never any real vault/notes
directory a user configures elsewhere. The LLM client, memory/context
helpers, and prompt module it references are yours to wire up (see
README.md).

send_briefing: a Level 3 example, not invoked by the example agent - exists
to demonstrate the Level-3 approval gate, not to send anything unattended.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from pathlib import Path

from core.control_plane.config_loader import ConfigNotFoundError, load_config
from core.filesystem import register_root, safe_path
from core.logger import get_logger

log = get_logger("agent_implementations")

BRIEFING_OUTPUT_ROOT_ID = "briefing_output"
register_root(BRIEFING_OUTPUT_ROOT_ID, Path("instance/runtime/briefings"))


async def project_status_impl(**_: Any) -> dict[str, Any]:
    # not part of this minimal release - wire up your own project-registry
    # route and update this import once you've built one.
    from api.routes.control_plane.projects import list_projects  # type: ignore[import-not-found]

    return await list_projects()


async def read_home_state_impl(**_: Any) -> dict[str, Any]:
    try:
        return load_config("home_state.yaml") or {}
    except ConfigNotFoundError:
        return {}


async def git_status_impl(project_id: str, **_: Any) -> dict[str, Any]:
    # not part of this minimal release - see project_status_impl above.
    from api.routes.control_plane.git_status import git_status as git_status_route  # type: ignore[import-not-found]

    return await git_status_route(project_id)


async def create_briefing_impl(focus: str = "all", **_: Any) -> dict[str, Any]:
    # not part of this minimal release - wire up your own LLM client,
    # memory/context store, and prompt helpers, then update these imports.
    from core.llm import acall  # type: ignore[import-not-found]
    from core.memory import search  # type: ignore[import-not-found]
    from core.obsidian import read_context, read_tasks  # type: ignore[import-not-found]
    from skills.assistant.briefing import SYSTEM, _parse, _sanitize_text  # type: ignore[import-not-found]

    today = str(date.today())
    context = read_context()
    tasks = read_tasks()
    memories = "\n".join(search("recent activity projects", n=3))

    prompt = f"""Generate the daily briefing for {today}.

Permanent context:
{context[:800] if context else "No context file yet"}

Current tasks:
{tasks[:600] if tasks else "No tasks file yet"}

Recent memory:
{memories[:400] if memories else "No recent memory"}

Focus today: {focus}

Return JSON exactly in this schema:
{{
  "greeting": "casual good morning",
  "date": "{today}",
  "top_3_priorities": ["...", "...", "..."],
  "projects_status": [
    {{"project": "...", "status": "...", "next_action": "..."}}
  ],
  "reminder": "anything important to not forget today",
  "telegram_message": "full formatted message, ready to send (Markdown, <= 1200 chars)"
}}"""

    raw = await acall(SYSTEM, prompt, model="default", skill="create_briefing", temperature=0.2, max_tokens=1200)
    result = _parse(raw)

    message = _sanitize_text(str(result.get("telegram_message") or raw))
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    out_path = safe_path(BRIEFING_OUTPUT_ROOT_ID, f"{ts}.md")
    out_path.write_text(f"# Briefing — {today}\n\n{message}", encoding="utf-8")

    log.info("create_briefing generated, written to %s (not the real vault)", out_path)
    result["_written_to"] = str(out_path)
    return result


async def send_briefing_impl(message: str, **_: Any) -> dict[str, Any]:
    """Level 3. Not invoked by any example agent in this release - exists
    to prove the Level-3 approval gate, not to actually message anyone
    unattended. Not part of this minimal release - wire up your own
    notification client and update this import."""
    from core.telegram import send  # type: ignore[import-not-found]

    ok = await send(message)
    return {"sent": ok}


IMPLEMENTATIONS: dict[str, Any] = {
    "project_status": project_status_impl,
    "read_home_state": read_home_state_impl,
    "git_status": git_status_impl,
    "create_briefing": create_briefing_impl,
    "send_briefing": send_briefing_impl,
}
