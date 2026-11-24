# Source

- Upstream: https://github.com/codepawl/creator-generalist (`plugins/3d-generalist/skills/use-3d-software`)
- Commit: `c0d3ff2f324820c18086c36bb4db431371154b8a`
- Licence: MIT (`LICENSE`, copied unchanged). Files copied unchanged.
- Security grade on agentskillshub.top: safe. The scripts were read before vendoring: `mesh_prep.py` installs npm
  packages and uses `uv` only when you run its mesh tools; nothing runs on load.

Why it is here: exact, current Blender 5.x and three.js steps for realistic materials (glass, ceramic, metal,
skin), lighting, depth of field, motion blur, HDRI worlds and headless renders. It is a tool skill: the look still
comes from `nutrition-hub-white-glass`. It mentions sibling skills of its plugin (3d-generalist and others) that
are not installed here; ignore those references.
