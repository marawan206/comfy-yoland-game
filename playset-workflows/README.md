# Playset environment workflows

Comfy workflows for generating 2D isometric environment assets: props, floor tiles, wall tiles,
walls with doors or windows, and wall decals. Characters, animation, music and sfx are Doug's
workflows and are not in this package.

## What is here

    workflows/playset_prop.api.json          one object sprite, transparent background
    workflows/playset_floor.api.json         one seamless square floor or ground texture
    workflows/playset_wall.api.json          one seamless flat wall texture
    workflows/playset_wall_opening.api.json  a flat wall section with a door or window drawn in
    workflows/playset_decal.api.json         one flat wall-mounted object, transparent background
    prompt_map.json                          frontend brief ids -> prompt text (styles, settings, palettes)
    reference/                               backend reference code and example data
    examples/                                outputs from these workflows and two assembled levels

All five are also saved in Comfy Cloud under the same names (playset_prop, playset_floor, ...).
Workflow ids are in workflow_ids.json.

## How to call them

Every workflow has the same shape, so the caller only chooses which one to run.

    node 1  INPUT  asset   what to draw            "ASSET: a stone chest with iron bands. Footprint 1 by 1 tiles, about 1 tile tall."
    node 2  INPUT  style   the art style text      from prompt_map.json styles[brief.style]
    node 3  INPUT  world   setting + palette text  from prompt_map.json settings[...] + palette sentence + brief.details
    node 4  FIXED  rules   per-type rules          do not change; this is what makes the output usable in a game
    node 8         model   GPT Image 2.5 Flare     inputs "model.size", "model.quality", "model.background"
    node 9  OUTPUT image   SaveImage

To run one, take the API JSON, overwrite `inputs.value` on nodes 1, 2 and 3, and submit it.
That is the whole injection. Example override body:

    { "1": { "value": "ASSET: ..." }, "2": { "value": "ART STYLE: ..." }, "3": { "value": "WORLD: ..." } }

Optional overrides on node 8: `model.quality` (low, medium, high), `model.size`.
Leave `model.background` alone: props and decals are transparent, textures are opaque.

For a prop, put the footprint and height in the asset text ("Footprint 2 by 1 tiles, about
1.5 tiles tall"). It guides proportions and the backend needs the same numbers later.

One run makes one asset. A pack is many runs. Run them in parallel and show them as they land.

## Mapping the frontend brief

    brief.perspective   isometric only. It is written into the fixed rules.
    brief.style[]       one run per style per asset. Text comes from prompt_map.json styles.
    brief.setting       prompt_map.json settings
    brief.palette       prompt_map.json palettes -> "Use only these colours and close tints of them: #.., #.."
    brief.details       appended to the world text
    brief.reference     NOT wired. The Flare node accepts reference images but that path is not built or tested.
    brief.pack          tiles -> playset_floor and playset_wall (the asset list must say which)
                        props -> playset_prop
                        wall doors and windows -> playset_wall_opening
                        wall-mounted items -> playset_decal
                        sheets, anim, sfx, music -> Doug's workflows
                        icons, bg -> not packaged yet (rules for them are in prompt_map.json)

Something has to turn the brief ids into the three strings. That is a small lookup in the app
backend using prompt_map.json, or an LLM call that also writes the asset list.

## What the backend must do after generation

Comfy makes pictures. Geometry and metadata are code. reference/mock_levels.py does all of
this end to end and is the thing to read.

    floors        spread one texture across a 4x4 block of tiles (user adjustable), then rotate 45
                  degrees, squash height 50 percent. Result is exact 2:1 diamonds, tile 128x64.
    walls         resize to N tiles wide, shear by half a pixel per column along the room edge.
                  Back edges (north, west) full height, near edges (south, east) low stubs.
    wall opening  same as a wall, but it replaces the plain wall on the tiles it covers.
    doorways      tiles where no wall is drawn, so rooms connect.
    decals        shear like a wall and paste onto a full-height wall.
    props         alpha threshold (>=200 -> 255, <=40 -> 0), trim, flip if the long side runs the wrong
                  way for the footprint, scale to fit the iso box of footprint x height
                  (reference/asset_meta.json), anchor at the front corner of the footprint,
                  draw everything back to front.
    checks        tile a texture 2x2 and score the seam (Anne's wrap score); regenerate above a threshold.

## What was tested, and what was not

Tested today, all at 1024 px, quality low:
- about 130 images through these prompts in two styles (risograph halftone, 16-bit pixel art)
- props come back with real transparency; style holds across a set from text alone
- floors and walls project into diamonds and sheared panels with no gaps
- one texture over 4x4 tiles hides repetition and seams well
- two full levels assembled from generated assets (examples/)
- all five saved workflows run from Comfy Cloud, including an input override

Known limits:
- Prop angle. The model draws roughly isometric, measured median 29.4 degrees with about 3 degrees
  of scatter, not exact 2:1 (26.6). Invisible on small or organic props, visible on long
  straight-edged ones. A uniform vertical squash to 86.6 percent moves the median onto 2:1.
  reference/measure_prop_angles.py measures any batch. The 2:1-only prompt wording used here
  has not been measured yet.
- Prop facing is not reliable. Most face lower-right as asked, some face lower-left. The backend flips.
- Scale is arbitrary per image. The backend rescales from footprint and height.
- Seams. Small, evenly scattered detail wraps well. Asking for big bold detail roughly doubles
  seam error and pulls plain surfaces off-brief. The WAS node "Image Seamless Texture" blends
  edges and ghosts flat graphic styles, so it is not used.
- Plain surfaces sometimes come back decorated (a "cream wall" came back as floral wallpaper).
  Say "completely plain, no pattern" and give a hex colour.
- The Flare seed input is not implemented, so "regenerate with a new seed" is just "run again".
- Not tested: 2048 px output, medium or high quality, reference images, the pixel, paper and clay
  style texts in prompt_map.json, anything other than isometric.
- No transition or autotile sets. Floors meet with hard edges.
- Pixel art: the model draws large fake pixels that are not on a true grid. For real pixel art,
  downscale with nearest neighbour and snap to the chosen palette in the backend.

## Cost and speed

Low quality at 1024 px took roughly 10 to 25 seconds per image. Batches ran about one job at a
time on the account used today, so 30 images took about 5 minutes. Every run is a paid
partner-API call billed to whichever Comfy account submits it.
