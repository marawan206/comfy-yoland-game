# Comfy Org: The Move

An 8-bit isometric story game about Comfy Org moving from the lavender Victorian house
to 201 Spear Street, Suite 1700, San Francisco. Starring Yoland. Featuring Deep, who can
no longer lock himself out of the office.

Built in an hour for the Comfy hackathon. All pixel art was generated with ComfyUI
(GPT Image 2.5 Flare through the Playset workflows in `playset-workflows/`).

## Play

Open `index.html` from any static host (it fetches `levels/*.json`, so it needs http, not file://).

    python -m http.server 8000

- WASD / arrows: move (isometric: up = north-east)
- E / Space / Enter: talk / advance
- M: mute
- Touch: on-screen d-pad and TALK button

## How it works

- `tools/build_levels.py` ports the asset pack's `mock_levels.py`: it reads `comfy-office-assets/*/level.json`,
  projects floors to 2:1 isometric, shears wall textures, scales props to their footprints and writes
  `levels/<name>/floor.jpg`, `atlas.png` and `level.json` (every wall segment / prop / decal with a depth,
  plus a walkability grid and blocked-edge bitmask).
- `game.js` renders the floor, then draws the atlas sprites depth-sorted with Yoland inserted between them,
  runs grid movement with wall collision, hotspots, the dialogue system and all sound (WebAudio square/triangle
  oscillators, no audio files).
