#!/usr/bin/env python3
"""Turn the on-chain PNGs into 9x9 bitmaps.

Each token's image is a 900x900 PNG of the grid at 100x magnification, stored as base64
inside the base64 tokenURI. Nearest-neighbour down to 9x9 is exact, not approximate: every
cell is a solid block of one colour and 900 = 9 * 100.

The metadata also carries a "Black Pixels" attribute, which gives a free integrity check on
the decode. If the count from the image disagrees with the count from the attributes, the
decode is wrong and we want to know rather than quietly build a table on top of it.
"""
import base64
import io
import json

import numpy as np
from PIL import Image

CELL = 100  # 900 / 9


def grid_from_png(b64):
    im = Image.open(io.BytesIO(base64.b64decode(b64)))
    w, h = im.size
    if (w, h) != (9 * CELL, 9 * CELL):
        raise ValueError(f"unexpected image size {w}x{h}")
    a = np.asarray(im.convert("L"))
    # Sample the centre of each cell rather than resizing, so no filter can blur a boundary.
    g = a[CELL // 2::CELL, CELL // 2::CELL]
    if g.shape != (9, 9):
        raise ValueError(f"bad sample shape {g.shape}")
    if not set(np.unique(g)) <= {0, 255}:
        raise ValueError(f"not monochrome: {sorted(set(np.unique(g)))[:6]}")
    return (g == 0).astype(np.uint8)  # 1 = black


def main():
    toks = json.load(open("tokens.json"))
    out, bad = {}, []
    for k in sorted(toks, key=int):
        t = toks[k]
        g = grid_from_png(t["png_b64"])
        stated = next(a["value"] for a in t["attributes"] if a["trait_type"] == "Black Pixels")
        if int(g.sum()) != int(stated):
            bad.append((k, int(g.sum()), stated))
        out[k] = {
            "name": t["name"],
            "owner": t["owner"],
            "black": int(g.sum()),
            "rarity": next(a["value"] for a in t["attributes"] if a["trait_type"] == "Rarity"),
            "rows": ["".join(str(v) for v in row) for row in g],
        }
    json.dump(out, open("grids.json", "w"), indent=0)
    print(f"{len(out)} grids written to grids.json")
    print(f"black-pixel counts agree with on-chain attributes: "
          f"{'yes, all ' + str(len(out)) if not bad else 'NO — ' + str(bad[:5])}")
    counts = np.array([v["black"] for v in out.values()])
    print(f"black pixels: min {counts.min()} median {int(np.median(counts))} max {counts.max()}")


if __name__ == "__main__":
    main()
