"""Pre-render the two office levels into game data.

For each level writes game/levels/<name>/floor.png, atlas.png and level.json.
Ported from comfy-office-assets/reference/mock_levels.py: same geometry, but every wall
segment, decal and prop becomes an atlas sprite with a depth so the game can sort the
player in between them. Also computes walkability and blocked edges from the level.
"""
import json
import os

import numpy as np
from PIL import Image, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "comfy-office-assets")
OUT = os.path.join(ROOT, "levels")
TW, TH = 128, 64
HU = 70
F = 96
TILES_PER_TEXTURE = 4
WALL_H, STUB_H = 176, 40
WALL_TILES = 3
STUB_N, STUB_W = (226, 222, 214, 255), (198, 194, 187, 255)
META = json.load(open(os.path.join(ASSETS, "reference", "asset_meta.json")))


def find_asset(folder, name):
    if not name:
        return None
    for sub in ("props", "floors", "walls", "wall_openings", "decals", "title_card"):
        p = os.path.join(ASSETS, folder, sub, str(name) + ".png")
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
    w, h = strip.size
    out = Image.new("RGBA", (w, h + w // 2), (0, 0, 0, 0))
    for x in range(w):
        dy = x // 2 if falls_right else (w - 1 - x) // 2
        out.paste(strip.crop((x, 0, x + 1, h)), (x, dy))
    return out


def glassify(tex):
    a = np.array(tex.convert("RGBA"))
    dark = a[:, :, :3].astype(int).sum(axis=2) < 230
    a[:, :, 3] = np.where(dark, 255, 105)
    return Image.fromarray(a, "RGBA")


class Atlas:
    def __init__(self, width=2048):
        self.width = width
        self.x = self.y = self.row_h = 0
        self.images = []

    def add(self, im):
        w, h = im.size
        if self.x + w > self.width:
            self.x, self.y, self.row_h = 0, self.y + self.row_h + 1, 0
        pos = (self.x, self.y)
        self.images.append((im, pos))
        self.x += w + 1
        self.row_h = max(self.row_h, h)
        return pos

    def render(self):
        out = Image.new("RGBA", (self.width, self.y + self.row_h), (0, 0, 0, 0))
        for im, pos in self.images:
            out.paste(im, pos)
        return out


def build(folder, name):
    level = json.load(open(os.path.join(ASSETS, folder, "level.json")))
    gc, gr = level["grid"]
    ox, oy = gr * TW // 2, WALL_H + 60
    sx = lambda c, r: (c - r) * TW // 2 + ox
    sy = lambda c, r: (c + r) * TH // 2 + oy
    W, H = (gc + gr) * TW // 2, (gc + gr) * TH // 2 + oy + 60
    rooms = {r["id"]: r for r in level["rooms"]}
    atlas = Atlas()
    items = []
    cache = {}

    def put(im, x, y, depth, kind):
        key = id(im)
        if key not in cache:
            cache[key] = atlas.add(im)
        ax, ay = cache[key]
        items.append({"x": int(x), "y": int(y), "w": im.width, "h": im.height, "d": round(depth, 3), "ax": ax, "ay": ay, "k": kind})

    # floors
    flat = Image.new("RGBA", (gc * F, gr * F), (0, 0, 0, 0))
    walled = np.zeros((gr, gc), dtype=bool)
    covered = np.zeros((gr, gc), dtype=bool)
    walk = np.zeros((gr, gc), dtype=bool)
    for room in level["rooms"]:
        c0, r0, w, d = room["rect"]
        covered[r0:r0 + d, c0:c0 + w] = True
        walk[r0:r0 + d, c0:c0 + w] = True
        if find_asset(folder, room.get("wall")) and not room.get("wall_sides"):
            walled[r0:r0 + d, c0:c0 + w] = True
        p = find_asset(folder, room["floor"])
        patch = Image.new("RGBA", (w * F, d * F), (150, 150, 158, 255))
        if p:
            block = Image.open(p).convert("RGBA").resize((F * TILES_PER_TEXTURE,) * 2, Image.LANCZOS)
            for c in range(c0, c0 + w):
                for r in range(r0, r0 + d):
                    u, v = (c % TILES_PER_TEXTURE) * F, (r % TILES_PER_TEXTURE) * F
                    patch.paste(block.crop((u, v, u + F, v + F)), ((c - c0) * F, (r - r0) * F))
        flat.paste(patch, (c0 * F, r0 * F))
    iso = flat.rotate(-45, expand=True, resample=Image.BICUBIC).resize((W, (gc + gr) * TH // 2), Image.LANCZOS)
    floor = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    floor.alpha_composite(iso, (0, oy))

    # walls + blocked edges. block[r][c] bitmask: 1=N 2=S 4=W 8=E
    block = np.zeros((gr, gc), dtype=int)
    BIT = {"north": 1, "south": 2, "west": 4, "east": 8}
    OPP = {"north": ("south", 0, -1), "south": ("north", 0, 1), "west": ("east", -1, 0), "east": ("west", 1, 0)}

    def spans(key, room_id, side):
        out = {}
        for s in level.get(key, []):
            if s["room"] == room_id and s["side"] == side:
                for i in range(s.get("span", 1)):
                    out[s["at"] + i] = (s, i)
        return out

    def mark_blocked(c, r, side, passable):
        if passable:
            return
        block[r, c] |= BIT[side]
        o, dc, dr = OPP[side]
        nc, nr = c + dc, r + dr
        if 0 <= nc < gc and 0 <= nr < gr:
            block[nr, nc] |= BIT[o]

    tex_cache = {}

    def texture(path, size):
        key = (path, size)
        if key not in tex_cache:
            tex_cache[key] = Image.open(path).convert("RGBA").resize(size, Image.LANCZOS)
        return tex_cache[key]

    strip_cache = {}

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
                return
            full = False
        kind = "full" if full else "stub"
        if over:
            kind = over[0]["kind"]
        if var:
            kind = "variant"
        # a drawn wall blocks movement, unless it is a door variant (walk through it)
        passable = bool(var and "door" in var[0]["asset"])
        mark_blocked(c, r, side, passable)
        ckey = (room["id"], side, kind, i if kind == "variant" else ((c if along_cols else -r) % WALL_TILES))
        if ckey in strip_cache:
            seg = strip_cache[ckey]
        else:
            if kind == "stub":
                strip = Image.new("RGBA", (TW // 2, STUB_H), STUB_N if along_cols else STUB_W)
            elif kind == "variant":
                s, j = var
                tex = texture(find_asset(folder, s["asset"]), (s["span"] * TW // 2, WALL_H))
                j = j if along_cols else s["span"] - 1 - j
                strip = tex.crop((j * TW // 2, 0, (j + 1) * TW // 2, WALL_H))
            else:
                wall_name = over[0].get("asset") if over and over[0].get("asset") else room["wall"]
                tex = texture(find_asset(folder, wall_name), (WALL_TILES * TW // 2, WALL_H))
                idx = (c if along_cols else -r) % WALL_TILES
                strip = tex.crop((idx * TW // 2, 0, (idx + 1) * TW // 2, WALL_H))
                if kind == "glass":
                    strip = glassify(strip)
            if not along_cols and kind != "stub":
                strip = ImageEnhance.Brightness(strip).enhance(0.84)
            seg = shear(strip, falls_right=along_cols)
            strip_cache[ckey] = seg
        h = seg.height - TW // 4
        if side == "north":
            x, y, depth = sx(c, r), sy(c, r) - h, c + r - 0.6
        elif side == "west":
            x, y, depth = sx(c, r + 1), sy(c, r) - h, c + r - 0.6
        elif side == "south":
            x, y, depth = sx(c, r + 1), sy(c, r + 1) - h, c + r + 1.3
        else:
            x, y, depth = sx(c + 1, r + 1), sy(c + 1, r) - h, c + r + 1.3
        put(seg, x, y, depth, "wall")

    for room in level["rooms"]:
        if not find_asset(folder, room.get("wall")):
            continue
        c0, r0, w, d = room["rect"]
        for side in room.get("wall_sides", ["north", "west", "south", "east"]):
            for i in range(w if side in ("north", "south") else d):
                segment(room, side, i)

    # props and decals
    props = []
    for obj in level["objects"]:
        p = find_asset(folder, obj["asset"])
        if not p:
            print("  missing asset:", obj["asset"]); continue
        spr = trimmed(p)
        if "wall_of" in obj:
            c0, r0, w, d = rooms[obj["wall_of"]]["rect"]
            c, r = c0 + obj.get("at", 0), r0
            spr.thumbnail((obj.get("size", 72), obj.get("size", 72) + 24), Image.LANCZOS)
            spr = shear(spr, falls_right=True)
            put(spr, sx(c, r) + (TW // 2 - spr.width) // 2 + 2, sy(c, r) - WALL_H + obj.get("drop", 30), c + r - 0.5, "decal")
            props.append({"asset": obj["asset"], "cell": [c, r], "footprint": [1, 0], "decal": True})
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
            put(spr, cx - spr.width // 2, by - spr.height, c + w + r + d - 1, "prop")
            props.append({"asset": obj["asset"], "cell": [c, r], "footprint": [w, d]})
            if not obj.get("walkable"):
                walk[r:r + d, c:c + w] = False

    os.makedirs(os.path.join(OUT, name), exist_ok=True)
    bg = Image.new("RGBA", floor.size, (236, 232, 224, 255))
    bg.alpha_composite(floor)
    bg.convert("RGB").save(os.path.join(OUT, name, "floor.jpg"), quality=88)
    atlas.render().save(os.path.join(OUT, name, "atlas.png"), optimize=True)
    data = {
        "name": name,
        "grid": [gc, gr],
        "origin": [ox, oy],
        "size": [W, H],
        "tile": [TW, TH],
        "player_start": level["player_start"],
        "rooms": [{"id": r["id"], "rect": r["rect"]} for r in level["rooms"]],
        "walk": walk.astype(int).tolist(),
        "block": block.tolist(),
        "props": props,
        "items": items,
    }
    json.dump(data, open(os.path.join(OUT, name, "level.json"), "w"))
    print(name, "items", len(items), "atlas", atlas.render().size, "floor", floor.size)


if __name__ == "__main__":
    build("old-office", "old")
    build("new-office", "new")
    # hero + title card
    hero = Image.open(os.path.join(ASSETS, "reference", "yoland_frame.png")).convert("RGBA")
    hero.save(os.path.join(OUT, "yoland.png"))
    title = os.path.join(ASSETS, "old-office", "title_card", "victorian_house_facade_5x4.png")
    t = trimmed(title)
    t.thumbnail((640, 640), Image.LANCZOS)
    t.save(os.path.join(OUT, "title.png"), optimize=True)
