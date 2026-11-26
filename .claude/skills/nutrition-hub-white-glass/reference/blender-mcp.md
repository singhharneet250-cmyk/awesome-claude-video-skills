# Blender MCP: Claude drives Blender on your computer

The `blender` server in this repo's `.mcp.json` lets Claude Code inspect and change the scene
in a running Blender, look through its camera, and render. Claude can build and light a product
or molecule scene in the Liquid Glass look while you watch, instead of you clicking through menus.

- **Package:** [`mcp-for-blender`](https://github.com/ahujasid/mcp-for-blender) (MIT, by Siddharth Ahuja;
  not affiliated with the Blender Foundation). It was called `blender-mcp` before.
- **Pinned to 2.2.7** (4 Nov 2026). Update only on purpose (see the last section).
- **Where it works:** on the computer where Blender runs. It talks to Blender on `localhost:9876`, so a
  cloud session has no Blender to reach.

## What's set in `.mcp.json` and why

| Setting | Why |
|---|---|
| `mcp-for-blender==2.2.7` | A fixed, reviewed version instead of whatever is newest |
| `--python 3.11`, `UV_PYTHON_PREFERENCE=only-managed` | The package's own advice: avoids conda/pyenv clashes on Windows and Mac |
| `DISABLE_TELEMETRY=true` | Without it, the server sends an anonymous usage record (tool names, timings, versions, OS) to the developer's database. With it, nothing is sent. |
| `BLENDER_MCP_SAFE_MODE=1` | Claude's Blender scripts are checked before they run. Reading or writing files directly, running programs, network access and code that keeps running are blocked. Modelling, materials, lighting, rendering, saving and import/export still work. |

These were checked in the 2.2.7 source, not just its README.

## Set up once (about 10 minutes)

1. **Install Blender 5.2** from blender.org, and **uv**:
   - Mac or Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows: `winget install --id=astral-sh.uv -e`
   - Then open a new terminal.
2. **Install the Blender add-on**, the same version as the server:
   `uvx mcp-for-blender==2.2.7 install-addon`. It copies the add-on into Blender's add-ons folder and keeps
   a `.bak` of anything it replaces. Skip the project's one-line `curl … | sh` installer: it rewrites every
   AI app's settings with an unpinned version.
3. **Turn on the add-on in Blender:**
   - Go to Edit → Preferences → Add-ons and turn on **Interface: MCP for Blender**.
   - Leave **telemetry consent** unticked.
   - Leave **Allow Remote Connections** off. With it on, anyone on your network could run code inside Blender.
4. **Start the add-on's server:** in the 3D view, press **N** → **MCP for Blender** tab → **Start MCP Server**
   (some versions say **Connect to Claude**).
5. **Connect Claude Code:** open this repo in Claude Code on the same computer (the desktop app, or `claude` in
   a terminal). Approve the project server **blender** when asked; `/mcp` shows whether it's connected.
   Don't run the `uvx` server command yourself, because Claude Code starts it.
6. **Test:** ask "check the Blender connection". Claude runs `get_addon_status` and reports the Blender and
   add-on versions.

## What Claude can do with it

| Tool | Used for |
|---|---|
| `get_scene_info` | Read the scene: objects, materials, lights, camera |
| `execute_blender_code` | Build and change things with Blender Python: geometry, Liquid Glass materials, lights, camera, animation, render settings |
| `look` | See the result through the viewport or the camera, from several angles, or as an animation strip, in solid, material or rendered mode. It also shows a render. |
| `search_assets`, `import_asset` | Poly Haven HDRIs and textures (CC0), Sketchfab and Poly Pizza models (licence varies) |
| `generate_3d` | AI-generated models (Tripo, Hunyuan3D, Rodin, Meshy). Restricted, see below. |
| `get_addon_status` | Versions and which options are on |

## Rules for Nutrition Hub work

- **Save the .blend first.** `execute_blender_code` can change or delete anything in the open file.
  Work in a copy for experiments.
- **Products and labels stay real.** Use the real cut-out photo or a real scan, as in SKILL.md §4 D.
  - Never use `generate_3d` for packaging, labels, logos, people's bodies or results.
  - Never use `generate_3d` for any model of a branded product, ours or anyone else's.
  - For a neutral prop (a shaker, a scoop, a gym plate), use it only with your OK: the premium generators cost
    money and send the prompt to a third party.
- **Assets:**
  - Poly Haven HDRIs and textures are CC0, so they're fine to use.
  - Sketchfab and Poly Pizza models each have their own licence. Use CC0 or CC-BY (with a credit) only;
    never NC (non-commercial), because this is a business.
- **The look is Liquid Glass:**
  - White and ice-mist studio, ceramic and frosted-glass materials, one orange accent.
  - Soft high-key light, no neon or dark sci-fi.
  - The constants are in `molecular-film/SKILL.md`; the motion rules are in SKILL.md §5.
- **Check by looking:** after each change, `look` through the camera in material or rendered mode, and read
  the picture rather than the code.
- **Final renders:**
  - Full-length films go through the molecular-film pipeline (`pipeline.py`) or a planned Cycles render,
    not one MCP call.
  - A long render inside the live session freezes Blender until it finishes.
- **Safe mode stays on.** If a step needs file access inside Blender (loading a downloaded structure,
  running the molecular-film pipeline), do that step from the terminal instead.
  - If safe mode has to be off for one session, say so first.
  - Edit `.mcp.json` to `"0"` only on your computer, and set it back to `"1"` afterwards.

## Updating

Read the release notes on GitHub first. Then change the version in `.mcp.json` and re-run
`uvx mcp-for-blender==<new version> install-addon`, so the add-on and the server match. Restart Claude Code and
Blender (Start MCP Server again).
