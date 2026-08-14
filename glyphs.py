#!/usr/bin/env python3
"""Build the corpus of shapes a 9x9 grid could plausibly be read as.

Three sources:

  font   A-Z, a-z, 0-9, punctuation and a set of Unicode pictographs, rendered from
         DejaVu Sans Bold at high resolution and area-averaged down. A cell is black
         when the glyph's ink covers at least half of it. This is the same question a
         human squints at: "if you drew this letter on a 9x9 grid, which cells fill in?"

  cjk    a short hand-picked list of Han characters that are actually grid-shaped
         (one, ten, mouth, sun, field, mountain...). Most characters turn to mush at
         9x9; these do not. Rendered the same way from the Droid fallback font.

  drawn  pixel-art pictograms I drew by hand, because no font contains them: an
         invader, a cat, a rocket, a skull. These are the shapes most likely to match,
         since unlike font glyphs they were designed for a grid this size.

Each shape is emitted at three scales (filling 9, 7 and 5 cells on its long side) and
at every position that keeps it inside the grid, so a small shape sitting in a corner
still counts as a match. No rotations and no mirroring: a mirrored E is not an E, and
allowing either would roughly double the number of chances every grid gets to look
like something, which is exactly the effect the null model in match.py exists to
measure rather than to inflate.

Writes corpus.json:  {"variants": [{"name","fit","dx","dy","bits"}...], "shapes": {...}}
"""
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont

N = 9
FITS = (9, 7, 5)
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FALLBACK = "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"

PUNCT = "+-=/\\*#?!&@%$<>^~|()[]{}.,:;'\""
SYMBOLS = ("♥♦♣♠"          # card suits
           "☺☹☼☀☽"    # faces, sun, moon
           "★☆⚑⚓⚡"    # stars, flag, anchor, bolt
           "♪♫☠☢☣"    # notes, skull, radiation, biohazard
           "→←↑↓"          # arrows
           "✓✗✚❄❤")   # check, ballot x, cross, snowflake, heart
CJK = "一二三十口日目田中山大人木上下工王土十州"

# Hand-drawn pixel art. '#' is black.
DRAWN = {
    "invader": [
        "..#...#..", "...#.#...", "..#####..", ".##.#.##.", "#########",
        "#.#####.#", "#.#...#.#", "...#.#...", "..#...#..",
    ],
    "heart": [
        ".##...##.", "#########", "#########", "#########", ".#######.",
        "..#####..", "...###...", "....#....", ".........",
    ],
    "smiley": [
        "..#####..", ".#.....#.", "#..#.#..#", "#.......#", "#.#...#.#",
        "#..###..#", ".#.....#.", "..#####..", ".........",
    ],
    "cat": [
        "##.....##", "###...###", "#########", "#.#...#.#", "#########",
        "#.#####.#", "#..###..#", ".#.....#.", "..#####..",
    ],
    "tree": [
        "....#....", "...###...", "..#####..", ".#######.", "#########",
        "...###...", "....#....", "....#....", "...###...",
    ],
    "house": [
        "....#....", "...###...", "..#####..", ".#######.", "#########",
        "#.#####.#", "#.##.##.#", "#.##.##.#", "#####.###",
    ],
    "arrow_up": [
        "....#....", "...###...", "..#####..", ".#######.", "####.####",
        "...###...", "...###...", "...###...", "...###...",
    ],
    "star5": [
        "....#....", "....#....", "...###...", "#########", ".#######.",
        "..#####..", "..#.#.#..", ".##...##.", "#.......#",
    ],
    "plus": [
        "...###...", "...###...", "...###...", "#########", "#########",
        "#########", "...###...", "...###...", "...###...",
    ],
    "ex": [
        "##.....##", "###...###", ".###.###.", "..#####..", "...###...",
        "..#####..", ".###.###.", "###...###", "##.....##",
    ],
    "checker": [
        "#.#.#.#.#", ".#.#.#.#.", "#.#.#.#.#", ".#.#.#.#.", "#.#.#.#.#",
        ".#.#.#.#.", "#.#.#.#.#", ".#.#.#.#.", "#.#.#.#.#",
    ],
    "diagonal": [
        "#........", "##.......", ".##......", "..##.....", "...##....",
        "....##...", ".....##..", "......##.", ".......##",
    ],
    "spiral": [
        "#########", "#.......#", "#.#####.#", "#.#...#.#", "#.#.#.#.#",
        "#.#.###.#", "#.#.....#", "#.#######", "#........",
    ],
    "frame": [
        "#########", "#.......#", "#.......#", "#.......#", "#.......#",
        "#.......#", "#.......#", "#.......#", "#########",
    ],
    "skull": [
        ".#######.", "#########", "#.##.##.#", "#.##.##.#", "#########",
        "#..###..#", "#########", ".#.#.#.#.", ".#######.",
    ],
    "ghost": [
        "..#####..", ".#######.", "##.###.##", "##.###.##", "#########",
        "#########", "#########", "#########", "#.#.#.#.#",
    ],
    "mushroom": [
        "..#####..", ".#######.", "#########", "#.#####.#", "#########",
        "...###...", "...###...", "...###...", "..#####..",
    ],
    "flower": [
        ".#.....#.", "##.###.##", "#########", ".#######.", "..#####..",
        "...###...", "....#....", "....#....", "...###...",
    ],
    "bird": [
        ".........", "..##.....", ".####....", "######...", "#######..",
        ".######..", "..####...", "...##....", ".........",
    ],
    "sailboat": [
        "....#....", "....##...", "....###..", "....####.", "....#####",
        ".........", "#########", ".#######.", "..#####..",
    ],
    "key": [
        ".###.....", "#...#....", "#...#....", ".###.....", "..#......",
        "..#......", "..###....", "..#......", "..###....",
    ],
    "hourglass": [
        "#########", ".#######.", "..#####..", "...###...", "....#....",
        "...###...", "..#####..", ".#######.", "#########",
    ],
    "rocket": [
        "....#....", "...###...", "..#####..", "..#.#.#..", "..#####..",
        "..#####..", ".#.###.#.", "#..###..#", "...#.#...",
    ],
    "pacman": [
        "..#####..", ".#######.", "##.######", "###.#####", "####.....",
        "###.#####", "##.######", ".#######.", "..#####..",
    ],
    "fish": [
        ".........", "..####...", ".######.#", "########.", "#########",
        "########.", ".######.#", "..####...", ".........",
    ],
    "eye": [
        ".........", "..#####..", ".#######.", "##.###.##", "##.#.#.##",
        "##.###.##", ".#######.", "..#####..", ".........",
    ],
    "yinyang": [
        "..#####..", ".###...#.", "###.#..##", "###...###", "#########",
        "##...####", "##..#.###", ".#...###.", "..#####..",
    ],
}


def render(ch, path):
    """High-resolution ink mask for one character, cropped to its bounding box."""
    size = 256
    try:
        f = ImageFont.truetype(path, size)
    except OSError:
        return None
    im = Image.new("L", (size * 3, size * 3), 0)
    ImageDraw.Draw(im).text((size, size // 2), ch, fill=255, font=f)
    box = im.getbbox()
    return im.crop(box) if box else None


def quantise(mask, fit):
    """Area-average an ink mask onto a fit-by-fit-bounded cell block; >=50% ink is black."""
    w, h = mask.size
    if h >= w:
        ch, cw = fit, max(1, round(fit * w / h))
    else:
        cw, ch = fit, max(1, round(fit * h / w))
    cov = np.asarray(mask.resize((cw, ch), Image.BOX), dtype=np.float32) / 255.0
    g = (cov >= 0.5).astype(np.uint8)
    if not g.any():                       # a hairline stroke never reaches half a cell
        g = (cov >= cov.max() * 0.999).astype(np.uint8)
    return g


def variants(g):
    """Every placement of a small bitmap inside the 9x9 grid."""
    h, w = g.shape
    for dy in range(N - h + 1):
        for dx in range(N - w + 1):
            c = np.zeros((N, N), np.uint8)
            c[dy:dy + h, dx:dx + w] = g
            yield dx, dy, c


def main():
    shapes = {}
    for ch in [chr(c) for c in range(65, 91)] + [chr(c) for c in range(97, 123)] + \
              [chr(c) for c in range(48, 58)] + list(PUNCT) + list(SYMBOLS):
        m = render(ch, SANS)
        if m is not None:
            shapes[f"'{ch}'"] = ("font", m)
    for ch in dict.fromkeys(CJK):
        m = render(ch, FALLBACK)
        if m is not None:
            shapes[f"'{ch}'"] = ("cjk", m)

    out, seen = [], {}
    for name, (kind, m) in shapes.items():
        for fit in FITS:
            g = quantise(m, fit)
            for dx, dy, c in variants(g):
                out.append((name, kind, fit, dx, dy, c))
    for name, rows in DRAWN.items():
        g = np.array([[1 if ch == "#" else 0 for ch in r] for r in rows], np.uint8)
        assert g.shape == (N, N), name
        out.append((name, "drawn", N, 0, 0, g))
        # also at reduced scale, so a small invader in a corner still registers
        for fit in FITS[1:]:
            q = quantise(Image.fromarray(g * 255), fit)
            for dx, dy, c in variants(q):
                out.append((name, "drawn", fit, dx, dy, c))

    # Collapse variants that produce byte-identical bitmaps. At this resolution many do
    # ('O', '0' and 'o' at fit 5 are one shape), and counting them separately would let a
    # grid claim several independent "matches" that are really one.
    variants_out = []
    for name, kind, fit, dx, dy, c in out:
        if not c.any() or c.all():
            continue                       # an all-white or all-black mask matches nothing
        key = c.tobytes()
        if key in seen:
            seen[key]["aliases"].append(name)
            continue
        v = {"name": name, "kind": kind, "fit": fit, "dx": dx, "dy": dy,
             "aliases": [], "bits": "".join("".join(map(str, r)) for r in c)}
        seen[key] = v
        variants_out.append(v)

    json.dump({"variants": variants_out}, open("corpus.json", "w"))
    kinds = {}
    for v in variants_out:
        kinds[v["kind"]] = kinds.get(v["kind"], 0) + 1
    print(f"{len(shapes)} font/cjk shapes + {len(DRAWN)} drawn")
    print(f"{len(out)} placements -> {len(variants_out)} distinct bitmaps "
          f"({len(out) - len(variants_out)} were duplicates)")
    print("by kind: " + ", ".join(f"{k} {n}" for k, n in sorted(kinds.items())))
    big = [v for v in variants_out if v["fit"] == 9]
    print(f"{len(big)} of them fill the whole grid")


if __name__ == "__main__":
    main()
