# OpenChatCut: a real timeline that Claude edits with you

[OpenChatCut](https://github.com/0xsline/OpenChatCut) is an open-source, local-first video editor with a
multi-track timeline, word-level transcript editing, captions, music and sound tracks, and exports to MP4,
SRT and FCPXML. The `openchatcut` server in this repo's `.mcp.json` lets Claude Code edit an open
project on your computer.
- **Draft first:** Claude's edits go into a draft.
- **You decide:** nothing changes on your timeline until you approve it in OpenChatCut.

- **Licence:** AGPL-3.0. Using it as an app is fine. Nothing of its code or skill files is copied into this repo,
  which keeps your repo's licence clean.
- **Version:** pin **v0.2.17** (15 Oct 2026), the latest release. Update on purpose (see the end).
- **Where it works:** on the computer where OpenChatCut runs. It listens on `localhost:5199`, so a cloud
  session can't reach it.
- **What was checked (repo at commit `f96502a`):**
  - The only "telemetry" in the code is a local log in the browser's storage ("no backend").
  - AI requests go only to the services you add keys for.
  - The MCP endpoint binds to your own computer.

## When to use it, and when to use this skill's scripts

| Job | Use |
|---|---|
| Rough cut you want to see and tweak: drop retakes and long pauses from the transcript, order the beats, place b-roll on a timeline | **OpenChatCut**, with Claude through MCP |
| A project you will keep editing by hand, or send to Final Cut / Premiere (FCPXML) | **OpenChatCut** |
| The White Glass finish: grade, bare matched captions (§6), orbit / frame escape / chat (§4 G–I), SFX kit, end card with the original logo, `qa.py` | **This skill's scripts**, on the MP4 exported from OpenChatCut |

The usual order: shoot, cut in OpenChatCut, export the MP4, then the White Glass finishing pass, then `qa.py`.

## Set up once

1. **Install OpenChatCut v0.2.17** from the GitHub Releases page (macOS DMG, Windows installer, Linux AppImage):
   `https://github.com/0xsline/OpenChatCut/releases/tag/v0.2.17`.
   - The builds are early and unsigned, so macOS asks you to approve the first launch.
   - Or run it from source at that tag with Node.js 24: `git clone --branch v0.2.17 …`, then `npm install`,
     then `npm run dev`.
2. **Open it and create or open a project.** It runs at `http://localhost:5199`.
3. **Connect Claude Code:** open this repo in Claude Code on the same computer and approve the project server
   **openchatcut**; `/mcp` shows whether it's connected.
   - The project's own router skill (`npx skills add 0xsline/OpenChatCut`) is optional: this guide covers what
     Claude needs.
   - If you install it, it isn't pinned to a version.
4. **Keys only for what you use:** add AI keys in OpenChatCut's Settings, never in chat.
   - Transcription and timeline editing of your own media work without any cloud key.
   - Cloud generation (Fal.ai, music, images) spends your credits. Use it only with your OK, and never for
     products, labels, logos or results (SKILL.md §4 D).

## How Claude edits (the draft and approval flow)

1. `openchatcut_status`, then `list_projects`. Pick the project you named; never guess.
2. `load_skill` for the specialised job (captions, transcript cuts, audio...): it is read-only.
3. `begin_edit_session` with **`approvalMode: "manual"`** (the default). Keep the `editSessionId` for every
   read and edit.
4. Make the edits in the draft.
5. `review_edit_session`. You preview the whole proposal in OpenChatCut and approve or reject it. It becomes
   one undo step.
6. Claude reports success only after `get_edit_session` says `applied`.

- **Approval stays manual.** Use `auto` (which applies without your review) only when you say so for that session.
- **What outside agents can't do:** generate media, export, delete projects or publish, so a rejected draft
  never leaves side effects. Export the MP4 yourself from the app.
- **If you ever open the endpoint to another device:** set `OPENCHATCUT_MCP_TOKEN` and keep it off the public
  internet.

## White Glass rules inside OpenChatCut

OpenChatCut can do many looks. This skill decides which ones Nutrition Hub uses (SKILL.md wins):

- **Transitions:**
  - Allowed: cuts, a soft dissolve, or a dip to porcelain white (0.3–0.5 s).
  - Never: glitch, whip pan, zoom punch, shake, light leaks, RGB split, spins (§5).
- **Captions:**
  - Either burn this skill's captions after export (`captions.py`, the bare matched-colour style), or build a
    named OpenChatCut caption style that matches §6: Inter bold, white, soft shadow, no box or pill, at most
    2 lines.
  - Don't use the app's pop or bounce caption presets.
- **Sound:**
  - Use this skill's SFX kit (`sfx.py --kit sfx_kit/`, then import the WAVs) at the §5 levels.
  - No scratch, boom or meme sounds.
  - Music sits 18–22 dB under the voice and must be licensed.
- **Online media search** (images, video, audio):
  - Use a clip only if its licence allows business use, and record the source.
  - Never use it for products or labels.
- **Logo and colours:**
  - Only the original logo file (§1), never re-drawn or recoloured.
  - Shader or LUT looks that push colours off the §2 palette or shift label colours are out.
- **Effects from this skill:**
  - Orbit, frame escape and chat run on the exported MP4.
  - Their renders (`render.cjs` overlays, `sfx.py` WAVs) can also be imported as media and placed on the timeline.

## Updating

Read the release notes first. Install the new release, change the version in this guide, and check that
Claude can still connect: `openchatcut_status` reports the server's required skill baseline.
