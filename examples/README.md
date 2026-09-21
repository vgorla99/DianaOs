# Examples

Everything here is fake/placeholder data, meant to be copied and edited,
never used as-is.

## instance.example/

Copy this whole directory to `instance/` at your repo root (gitignored -
never commit your real one):

```bash
cp -r examples/instance.example instance
```

### Your project registry

`instance/config/projects.yaml` - one entry per real project you want an
agent to be able to read about. `approved_paths.production` should point
to a real git repository on your machine if you want `git_status`-style
skills to work for that project. See the example file's comments for the
exact resolution rule (relative paths resolve under your home directory;
absolute paths are used as-is).

### Your allowed filesystem roots

Any skill that writes to disk does so through `core/filesystem/safe_path.py`.
Register a root once at startup:

```python
from core.filesystem import register_root

register_root("my_output", "path/to/a/directory")
```

then list that root's ID in both the skill's `allowed_roots` and the
agent's `allowed_roots` - `core/agents/runtime.py`'s dispatch lifecycle
requires both, plus that the root is actually registered.

### Your provider credentials and model/provider choice

Set in `.env` (see `.env.example` at the repo root) - this framework
itself doesn't call any LLM provider directly (no LLM client is included
in this release); wire up your own provider call inside your skill
implementations, keyed off whichever env vars you set.

### Your own Chief-of-Staff persona

`instance/config/agents/chief_of_staff.example.yaml` - copy it, rename it
if you like, and rewrite `persona_prompt` to be your own. `role` is a
structural discriminator only - never branch application logic on
`persona_prompt`'s contents, only on `role`.

### Your own private extensions

If you have brand- or business-specific logic, keep it in your own
package, never in `core/`. Reference it the same way
`core/skills/resolver.py`'s `LEGACY_COMPAT` example entry does - by
Python import path, resolved explicitly, never via dynamic
`importlib`/`getattr`-based discovery.

## instance.example/config/agents/chief_of_staff.example.yaml and instance.example/config/skills/example_skill.example.yaml

A minimal, working agent + skill pair, `enabled: false` by default -
validating a definition is not the same as activating it. Flip
`enabled: true` only once you've reviewed the allowlists yourself.
