"""Measure the ground-edge angles of generated isometric props.

For each transparent PNG in ./kit: take the lowest opaque pixel in every column, build the
lower convex hull of that outline, and report the angle of the longest hull edge on the
left side and on the right side. Those are the edges where the prop meets the floor.
2:1 game isometric = 26.57 degrees. True isometric = 30.00 degrees.
"""
import glob, math, os
import numpy as np
from PIL import Image

def lower_hull(pts):
    # pts sorted by x; image y grows downward, so the visual bottom is max y
    hull = []
    for p in pts:
        while len(hull) >= 2:
            (x1, y1), (x2, y2) = hull[-2], hull[-1]
            if (x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1) >= 0:
                hull.pop()
            else:
                break
        hull.append(p)
    return hull

rows = []
for f in sorted(glob.glob("kit/*.png")):
    a = np.array(Image.open(f).convert("RGBA"))[:, :, 3] > 128
    cols = np.where(a.any(axis=0))[0]
    pts = [(int(x), int(np.where(a[:, x])[0].max())) for x in cols]
    h = lower_hull(pts)
    width = cols.max() - cols.min()
    best = {"L": (0, None), "R": (0, None)}
    for (x1, y1), (x2, y2) in zip(h, h[1:]):
        dx, dy = x2 - x1, y2 - y1
        if dx < 0.12 * width or dy == 0:
            continue
        side = "L" if dy > 0 else "R"          # going right and down = left arm of the V
        ang = math.degrees(math.atan2(abs(dy), dx))
        if dx > best[side][0]:
            best[side] = (dx, ang)
    rows.append((os.path.basename(f)[:-4], best["L"][1], best["R"][1]))

print(f"{'prop':26s} {'left edge':>10s} {'right edge':>11s}")
vals = []
for n, l, r in rows:
    fmt = lambda v: f"{v:6.1f}" if v is not None else "   n/a"
    print(f"{n:26s} {fmt(l):>10s} {fmt(r):>11s}")
    vals += [v for v in (l, r) if v is not None]
v = np.array(vals)
print(f"\nedges measured: {len(v)}   median {np.median(v):.1f}   mean {v.mean():.1f}   min {v.min():.1f}   max {v.max():.1f}")
print(f"within 1.5 deg of 26.57 (2:1): {(abs(v-26.57)<=1.5).sum()}   within 1.5 deg of 30.0: {(abs(v-30)<=1.5).sum()}   neither: {((abs(v-26.57)>1.5)&(abs(v-30)>1.5)).sum()}")
