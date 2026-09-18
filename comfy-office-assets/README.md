# Comfy office assets

Generated isometric assets for the two Comfy office demo levels: the old office (the lavender
Victorian house) and the new office (the high-rise floor). 16-bit pixel art, made with GPT Image
2.5 Flare through the Playset workflows, 1024 px, quality low.

    new-office/   old-office/
        floors/          seamless square textures, top-down. The app projects them into 2:1 diamonds.
        walls/           seamless flat wall textures, front-on. The app shears them along room edges.
        wall_openings/   flat wall sections with a door or window drawn in. They replace the plain wall
                         on the tiles they cover.
        props/           transparent sprites. The file name ends in the footprint, e.g. desk_pod_four_4x2.
        decals/          flat wall-mounted items (clock, portrait, screen), transparent.
        title_card/      old office only: the Victorian exterior, used as the level's title image.
        _superseded/     first attempts that were replaced. Kept for reference, not used in the level.
        manifest.json    every asset with type, file, footprint, height in tiles and whether the level uses it
        level.json       rooms, floors, walls, wall openings, doorways and prop placements
        level_mockup.png the level assembled from these assets

    reference/    mock_levels.py builds the mock-ups from level.json and the assets. asset_meta.json is
                  the prop height table. yoland_frame.png is one frame cut from a screenshot of Doug's
                  sprite sheet, a stand-in only.

Each office folder is self-contained. A few props are shared between the two levels (the office
chairs and the fridge) and are copied into both.

Things to know:
- Grid is 2:1 isometric, tile 128x64. Floors, walls and placement are exact because code does them.
- Props are drawn by the model at roughly 29 degrees, not exact 2:1, and facing is not always
  consistent. mock_levels.py flips a prop when its long side runs the wrong way.
- Prop images are not to scale with each other. Scale each one to fit the box of its footprint and
  height_tiles from the manifest.
- The mock-ups are static composites. Nothing is walkable yet and there is no collision.
- Some generated assets are not placed in a level yet (see used_in_level in the manifest).
- The source office photos are not included because they show team members.
