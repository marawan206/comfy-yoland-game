"""Static isometric mock-ups of the two office levels.

Reads levels.json, asset_meta.json and the generated assets in ./new and ./old, and writes
mock_new_office.png and mock_old_office.png. This is the geometry the app backend has to do:

  floors    flat square textures, one texture spread over a 4x4 block of tiles, projected to 2:1
  walls     flat front-on textures sheared along room edges. North and west edges are the back
            walls (full height unless another room is behind them, then a low stub). South and
            east edges are the near side, always a low stub so the room stays visible.
  variants  a wall texture with a window or door drawn in replaces the plain wall on some tiles
  doorways  tiles where no wall is drawn at all, so rooms connect
  glass     a full-height wall drawn see-through
  props     scaled to fit the isometric box of their declared footprint and height, flipped if
            their long side runs the wrong way, anchored at the front corner, drawn back to front
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
TW, TH = 128, 64            # tile diamond on screen
HU = 70                     # screen pixels per tile of height
F = 96                      # flat pixels per tile before projection
TILES_PER_TEXTURE = 4
WALL_H, STUB_H = 176, 40
WALL_TILES = 3              # a plain wall texture spreads over 3 tiles
STUB_N, STUB_W = (226, 222, 214, 255), (198, 194, 187, 255)
BG = (236, 232, 224)
META = json.load(open(os.path.join(HERE, "asset_meta.json")))


def find_asset(name):
    for folder in ("new", "old"):
        p = os.path.join(HERE, folder, str(name) + ".png")
        if os.path.exists(p):
            return p
    return None


def trimmed(path):
    im = Image.open(path).convert("RGBA")
    a = np.array(im)[:, :, 3]
    a = np.where(a >= 200, 255, np.where(a <= 40, 0, a)).astype(np.uint8)
    im.putalpha(Image.fromarray(a))
    return im.crop(Image.fromarray((a > 0).astype(np.uint8) * 255).getbbox())


def long_axis(im):
    """Which grid axis the prop's long side runs along, read from its floor outline."""
    a = np.array(im)[:, :, 3] > 128
    cols = np.where(a.any(axis=0))[0]
    pts = [(int(x), int(np.where(a[:, x])[0].max())) for x in cols]
    hull = []
    for p in pts:
        while len(hull) >= 2:
            (x1, y1), (x2, y2) = hull[-2], hull[-1]
            if (x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1) >= 0:
                hull.pop()
            else:
                break
        hull.append(p)
    down = sum(x2 - x1 for (x1, y1), (x2, y2) in zip(hull, hull[1:]) if y2 > y1)
    up = sum(x2 - x1 for (x1, y1), (x2, y2) in zip(hull, hull[1:]) if y2 < y1)
    return "col" if down >= up else "row"


def shear(strip, falls_right):
    """Shear a flat wall strip to the 2:1 slope. falls_right: the strip runs down-right on screen."""
    w, h = strip.size
    out = Image.new("RGBA", (w, h + w // 2), (0, 0, 0, 0))
    for x in range(w):
        dy = x // 2 if falls_right else (w - 1 - x) // 2
        out.paste(strip.crop((x, 0, x + 1, h)), (x, dy))
    return out


def glassify(tex):
    a = np.array(tex.convert("RGBA"))
    dark = a[:, :, :3].astype(int).sum(axis=2) < 230          # frame and mullions stay solid
    a[:, :, 3] = np.where(dark, 255, 105)
    return Image.fromarray(a, "RGBA")


def render(level, name):
    gc, gr = level["grid"]
    ox, oy = gr * TW // 2, WALL_H + 420
    sx = lambda c, r: (c - r) * TW // 2 + ox
    sy = lambda c, r: (c + r) * TH // 2 + oy
    canvas = Image.new("RGBA", ((gc + gr) * TW // 2, (gc + gr) * TH // 2 + oy + 60), BG + (255,))
    rooms = {r["id"]: r for r in level["rooms"]}

    # ---------------- floors
    flat = Image.new("RGBA", (gc * F, gr * F), (0, 0, 0, 0))
    walled = np.zeros((gr, gc), dtype=bool)      # covered by a room that draws walls
    covered = np.zeros((gr, gc), dtype=bool)
    for room in level["rooms"]:
        c0, r0, w, d = room["rect"]
        covered[r0:r0 + d, c0:c0 + w] = True
        if find_asset(room.get("wall")) and not room.get("wall_sides"):
            walled[r0:r0 + d, c0:c0 + w] = True
        p = find_asset(room["floor"])
        patch = Image.new("RGBA", (w * F, d * F), (150, 150, 158, 255))
        if p:
            block = Image.open(p).convert("RGBA").resize((F * TILES_PER_TEXTURE,) * 2, Image.LANCZOS)
            for c in range(c0, c0 + w):
                for r in range(r0, r0 + d):
                    u, v = (c % TILES_PER_TEXTURE) * F, (r % TILES_PER_TEXTURE) * F
                    patch.paste(block.crop((u, v, u + F, v + F)), ((c - c0) * F, (r - r0) * F))
        flat.paste(patch, (c0 * F, r0 * F))
    iso = flat.rotate(-45, expand=True, resample=Image.BICUBIC).resize(((gc + gr) * TW // 2, (gc + gr) * TH // 2), Image.LANCZOS)
    canvas.alpha_composite(iso, (0, oy))

    # ---------------- walls
    def spans(key, room_id, side):
        out = {}
        for s in level.get(key, []):
            if s["room"] == room_id and s["side"] == side:
                for i in range(s.get("span", 1)):
                    out[s["at"] + i] = (s, i)
        return out

    draw = []   # (depth, image, x, y)

    def segment(room, side, i):
        c0, r0, w, d = room["rect"]
        back = side in ("north", "west")
        along_cols = side in ("north", "south")
        c = c0 + i if along_cols else (c0 if side == "west" else c0 + w - 1)
        r = (r0 if side == "north" else r0 + d - 1) if along_cols else r0 + i
        if i in spans("doorways", room["id"], side):
            return
        var = spans("wall_variants", room["id"], side).get(i)
        over = spans("wall_overrides", room["id"], side).get(i)
        nb = {"north": (c, r - 1), "south": (c, r + 1), "west": (c - 1, r), "east": (c + 1, r)}[side]
        inside = 0 <= nb[0] < gc and 0 <= nb[1] < gr
        if back:
            full = not (inside and covered[nb[1], nb[0]])
        else:
            if inside and walled[nb[1], nb[0]]:
                return                       # the neighbouring room draws this shared wall itself
            full = False
        kind = "full" if full else "stub"
        if over:
            kind = over[0]["kind"]
        if var:
            kind = "variant"
        if kind == "stub":
            strip = Image.new("RGBA", (TW // 2, STUB_H), STUB_N if along_cols else STUB_W)
        elif kind == "variant":
            s, j = var
            tex = Image.open(find_asset(s["asset"])).convert("RGBA").resize((s["span"] * TW // 2, WALL_H), Image.LANCZOS)
            j = j if along_cols else s["span"] - 1 - j      # west and east strips run right to left on screen
            strip = tex.crop((j * TW // 2, 0, (j + 1) * TW // 2, WALL_H))
        else:
            wall_name = over[0].get("asset") if over and over[0].get("asset") else room["wall"]
            tex = Image.open(find_asset(wall_name)).convert("RGBA").resize((WALL_TILES * TW // 2, WALL_H), Image.LANCZOS)
            idx = (c if along_cols else -r) % WALL_TILES
            strip = tex.crop((idx * TW // 2, 0, (idx + 1) * TW // 2, WALL_H))
            if kind == "glass":
                strip = glassify(strip)
        if not along_cols and kind != "stub":
            strip = ImageEnhance.Brightness(strip).enhance(0.84)
        h = strip.height
        seg = shear(strip, falls_right=along_cols)
        if side == "north":
            x, y, depth = sx(c, r), sy(c, r) - h, c + r - 0.6
        elif side == "west":
            x, y, depth = sx(c, r + 1), sy(c, r) - h, c + r - 0.6
        elif side == "south":
            x, y, depth = sx(c, r + 1), sy(c, r + 1) - h, c + r + 1.3
        else:
            x, y, depth = sx(c + 1, r + 1), sy(c + 1, r) - h, c + r + 1.3
        draw.append((depth, seg, x, y))

    for room in level["rooms"]:
        if not find_asset(room.get("wall")):
            continue
        c0, r0, w, d = room["rect"]
        for side in room.get("wall_sides", ["north", "west", "south", "east"]):
            for i in range(w if side in ("north", "south") else d):
                segment(room, side, i)

    # ---------------- props, decals, player
    for obj in level["objects"]:
        p = find_asset(obj["asset"])
        if not p:
            print("  missing asset:", obj["asset"]); continue
        spr = trimmed(p)
        if "wall_of" in obj:
            c0, r0, w, d = rooms[obj["wall_of"]]["rect"]
            c, r = c0 + obj.get("at", 0), r0
            spr.thumbnail((obj.get("size", 72), obj.get("size", 72) + 24), Image.LANCZOS)
            spr = shear(spr, falls_right=True)
            draw.append((c + r - 0.5, spr, sx(c, r) + (TW // 2 - spr.width) // 2 + 2, sy(c, r) - WALL_H + obj.get("drop", 30)))
            continue
        w, d = obj["footprint"]
        want = obj.get("axis") or ("col" if w > d else "row" if d > w else None)
        flip = bool(obj.get("flip"))
        if want and long_axis(spr) != want:
            flip = not flip
        if flip:
            spr = spr.transpose(Image.FLIP_LEFT_RIGHT)
        h_tiles = META.get(obj["asset"], {}).get("height", 1.2)
        box_w, box_h = (w + d) * TW / 2, (w + d) * TH / 2 + h_tiles * HU
        k = min(box_w * 0.96 / spr.width, box_h / spr.height)
        spr = spr.resize((max(1, round(spr.width * k)), max(1, round(spr.height * k))), Image.LANCZOS)
        for c, r in obj.get("cells", [obj.get("cell")]):
            cx = (sx(c, r + d) + sx(c + w, r)) // 2
            by = sy(c + w, r + d) - 5
            draw.append((c + w + r + d - 1, spr, cx - spr.width // 2, by - spr.height))

    hero = os.path.join(HERE, "yoland_frame.png")
    if os.path.exists(hero):
        h = Image.open(hero).convert("RGBA")
        k = 1.65 * HU / h.height
        h = h.resize((round(h.width * k), round(h.height * k)), Image.LANCZOS)
        c, r = level["player_start"]
        draw.append((c + r + 1.05, h, sx(c, r) - h.width // 2, sy(c, r) + TH // 2 - h.height + 8))

    for _, im, x, y in sorted(draw, key=lambda t: t[0]):
        canvas.alpha_composite(im, (int(x), int(y)))

    diff = np.abs(np.array(canvas.convert("RGB")).astype(int) - np.array(BG)).sum(axis=2) > 12
    box = Image.fromarray(diff.astype(np.uint8) * 255).getbbox()
    pad = 40
    canvas = canvas.crop((max(0, box[0] - pad), max(0, box[1] - pad), min(canvas.width, box[2] + pad), min(canvas.height, box[3] + pad)))
    out = os.path.join(HERE, f"mock_{name}.png")
    canvas.convert("RGB").save(out)
    print(out, canvas.size)


if __name__ == "__main__":
    levels = json.load(open(os.path.join(HERE, "levels.json")))
    for key in ("new_office", "old_office"):
        if len(sys.argv) > 1 and sys.argv[1] != key:
            continue
        print(key)
        render(levels[key], key)
