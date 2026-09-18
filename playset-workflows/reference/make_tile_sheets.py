"""Preview sheets for square tile textures.

Reads every PNG in ./tiles and writes three images next to this script:
  tiles_flat_sheet.jpg   the raw square textures
  tiles_seam_sheet.jpg   each texture tiled 2x2 so edge seams show
  tiles_iso_sheet.jpg    each texture projected into 2:1 iso diamonds (land)
                         or skewed wall panels (wall), assembled as a small patch
This is the same geometry step the app backend has to do.
"""
import glob
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
TILE_W, TILE_H = 128, 64
PAPER = (243, 236, 222)


def diamond(tex):
    """Square texture -> one 2:1 iso diamond (rotate 45, squash height 50%)."""
    t = tex.convert("RGBA").resize((256, 256), Image.LANCZOS)
    r = t.rotate(45, expand=True, resample=Image.BICUBIC)
    return r.resize((TILE_W, TILE_H), Image.LANCZOS)


def _shear(t, side):
    """Skew a flat wall panel vertically by half a pixel per column (the 2:1 iso slope).

    side "left": the wall rises toward the right (it meets the back corner on its right edge).
    side "right": the wall falls toward the right (it leaves the back corner on its left edge).
    """
    w, h = t.size
    out = Image.new("RGBA", (w, h + w // 2), (0, 0, 0, 0))
    for x in range(w):
        col = t.crop((x, 0, x + 1, h))
        dy = (w - 1 - x) // 2 if side == "left" else x // 2
        out.paste(col, (x, dy))
    return out


def iso_patch(tex, n=4):
    d = diamond(tex)
    W = n * TILE_W
    H = n * TILE_H
    img = Image.new("RGBA", (W, H + 8), (0, 0, 0, 0))
    for row in range(n):
        for col in range(n):
            x = (col - row) * TILE_W // 2 + W // 2 - TILE_W // 2
            y = (col + row) * TILE_H // 2
            img.alpha_composite(d, (x, y))
    return img


def wall_patch(tex, n=3):
    flat = tex.convert("RGBA").resize((64, 128), Image.LANCZOS)
    left = _shear(flat, "left")
    right = _shear(flat, "right")
    # darken the right-hand wall slightly so the corner reads
    clear = Image.new("RGBA", right.size, (0, 0, 0, 0))
    shade = Image.composite(Image.new("RGBA", right.size, (22, 15, 40, 60)), clear, right.getchannel("A"))
    right = Image.alpha_composite(right, shade)
    img = Image.new("RGBA", (n * 64 * 2, 128 + n * 32), (0, 0, 0, 0))
    # left wall rises to the back corner in the middle, right wall falls away from it
    for i in range(n):
        img.alpha_composite(left, (i * 64, (n - 1 - i) * 32))
        img.alpha_composite(right, (n * 64 + i * 64, i * 32))
    return img


def sheet(items, cell_w, cell_h, cols, path, label=True):
    rows = (len(items) + cols - 1) // cols
    pad = 28 if label else 0
    out = Image.new("RGB", (cols * cell_w, rows * (cell_h + pad)), PAPER)
    dr = ImageDraw.Draw(out)
    for i, (name, im) in enumerate(items):
        cx, cy = (i % cols) * cell_w, (i // cols) * (cell_h + pad)
        im = im.convert("RGBA")
        im.thumbnail((cell_w - 16, cell_h - 16), Image.LANCZOS)
        out.paste(im, (cx + (cell_w - im.width) // 2, cy + (cell_h - im.height) // 2), im)
        if label:
            dr.text((cx + 10, cy + cell_h + 4), name, fill=(40, 30, 60))
    out.save(path, quality=90)
    return path


def main():
    files = sorted(glob.glob(os.path.join(HERE, "tiles", "*.png")))
    flat, seam, iso = [], [], []
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        tex = Image.open(f).convert("RGB")
        flat.append((name, tex))
        s = tex.resize((256, 256), Image.LANCZOS)
        two = Image.new("RGB", (512, 512))
        for ox in (0, 256):
            for oy in (0, 256):
                two.paste(s, (ox, oy))
        seam.append((name, two))
        iso.append((name, wall_patch(tex) if name.startswith("wall_") else iso_patch(tex)))
    print(len(files), "textures")
    print(sheet(flat, 300, 300, 5, os.path.join(HERE, "tiles_flat_sheet.jpg")))
    print(sheet(seam, 380, 380, 5, os.path.join(HERE, "tiles_seam_sheet.jpg")))
    print(sheet(iso, 540, 300, 4, os.path.join(HERE, "tiles_iso_sheet.jpg")))


if __name__ == "__main__":
    main()
