# DianaOS

DianaOS is the reusable public framework derived from the architecture
powering **Vitor Brain**, a private personal AI operating system. It lets
you configure your own projects, knowledge, agents, skills, permissions,
models, and local/private data - built by using the framework for real,
not designed in the abstract.

Nothing here depends on the name or persona "Diana" - the Chief-of-Staff
role (and any other agent) is fully configurable via YAML; "Diana" is kept
only as one example persona name in `examples/`.

## Current release scope

- core framework (`core/agents/`, `core/skills/`)
- managed agents/skills - explicit-load registries, no auto-discovery
- permissions/approvals - default-deny allowlists, a 5-level approval
  model (READ through CRITICAL), level 3+ always requires explicit
  approval
- safe filesystem primitives - one containment-checked write path, no
  exceptions
- audit/run-history foundations - append-only log, built-in secret
  redaction
- synthetic configuration examples (`examples/`)

**Not yet included:**

- full dashboard/UI
- full API product
- scheduler
- autonomous background agents
- connectors (LLM providers, messaging, external services)
- the private system's own business-specific extensions/data

Concretely, that means: `core/agents/implementations.py` ships 5 example
implementation functions, but 4 of them (`project_status_impl`,
`git_status_impl`, `create_briefing_impl`, `send_briefing_impl`) reference
imports that aren't part of this release yet (a project registry, an LLM
client, a notification client) - they're wiring examples to adapt, not
working code out of the box. Only `read_home_state_impl` runs standalone
today. This is deliberate, not an oversight.

## Build your own brain - quick start

```bash
pip install -r requirements.txt
cp -r examples/instance.example instance   # gitignored - never commit your real one
```

```python
import asyncio
from core.agents.registry import AgentRegistry
from core.skills.registry import SkillRegistry
from core.agents.runtime import dispatch

async def main():
    agents = AgentRegistry()
    agents.load("instance/config/agents")
    skills = SkillRegistry()
    skills.load("instance/config/skills")

    # this raises AgentDisabledError on a fresh copy - the shipped example
    # ships enabled: false on purpose (validating a definition is not the
    # same as activating it). Edit instance/config/agents/chief_of_staff.example.yaml
    # and set enabled: true once you've reviewed its allowlists, then re-run.
    result = await dispatch(agents, skills, "chief_of_staff", "example_skill", approved=True)
    print(result)

asyncio.run(main())
```

Edit `instance/config/projects.yaml`, `instance/config/agents/*.yaml`, and
`instance/config/skills/*.yaml` with your own projects, agent personas,
and skills - see `examples/README.md` for exactly what each file needs.

## Tests

```bash
python -m pytest
```

A synthetic, offline, deterministic test suite covering `safe_path`'s
containment guarantees, default-deny permission checks, skill
implementation resolution (including a structural check that no
YAML-controlled dynamic import exists), the approval-level gate, audit-log
secret redaction, and registry config loading. No real network, LLM,
credentials, or private data anywhere in it.

## License

Not yet set - to be added before public release.
