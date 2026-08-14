#!/usr/bin/env python3
"""Score every Binary Pixels grid against every shape, and say how surprised to be.

The score is the Matthews correlation coefficient between the grid's black cells and the
shape's black cells over all 81 positions. MCC rather than raw agreement because raw
agreement rewards a mostly-white shape on a mostly-white grid for the cells it never
claimed; MCC does not.

The part that matters is not the score, it is the null. Six thousand-odd shapes is a lot of
chances to look like something, and the best of six thousand tries is high even for noise.
So for every grid we shuffle its own cells at random -- keeping the black count exactly, so
the on-chain rarity is held fixed -- and take the best match over the same corpus, a few
hundred times. The reported p is the fraction of those shuffles that matched the corpus at
least as well as the real grid did.

A grid that scores 0.55 against a letter means nothing on its own. A grid that scores 0.55
when 96% of its own reshuffles score higher means the letter is in the eye of the beholder.

    python3 match.py            # leaderboard + per-token table
    python3 match.py --all      # every token, top 3 each
"""
import json
import sys

import numpy as np

N2 = 81
NULLS = 600
SEED = 20260814


def load_corpus():
    v = json.load(open("corpus.json"))["variants"]
    G = np.array([[int(c) for c in x["bits"]] for x in v], dtype=np.float32)
    return v, G


def load_grids():
    g = json.load(open("grids.json"))
    ids = sorted(g, key=int)
    V = np.array([[int(c) for c in "".join(g[i]["rows"])] for i in ids], dtype=np.float32)
    return g, ids, V


def scores(G, m, w, V, k):
    """MCC of every shape against every query column of V.

    Written out, MCC = (a*d - b*c) / sqrt((a+b)(a+c)(b+d)(c+d)) with a = |shape & grid|,
    b = m - a, c = k - a, d = 81 - m - k + a. Expanding the numerator, every quadratic term
    cancels and it collapses to 81a - m*k. That is the whole reason the null is affordable:
    one matrix product gives every intersection count, and the rest is arithmetic on scalars
    already in hand, so a few hundred thousand shuffles cost one 81-deep GEMM instead of
    six thousand set operations apiece.
    """
    A = G @ V.T                                   # (shapes, queries) intersection counts
    num = 81.0 * A - np.outer(m, k)
    return num * w[:, None] / np.sqrt(k * (81.0 - k))[None, :]


def best_null(G, m, w, k, rng, reps=NULLS):
    """Best-of-corpus score for `reps` reshuffles of a grid with k black cells."""
    if k == 0 or k == 81:
        return np.zeros(reps)                     # no variance to permute; MCC undefined
    out = np.empty(reps, dtype=np.float32)
    base = np.zeros(N2, dtype=np.float32)
    base[:k] = 1.0
    for s in range(0, reps, 200):
        e = min(s + 200, reps)
        block = np.stack([rng.permutation(base) for _ in range(e - s)])
        out[s:e] = scores(G, m, w, block, np.full(e - s, float(k))).max(axis=0)
    return out


def main():
    var, G = load_corpus()
    meta, ids, V = load_grids()
    m = G.sum(axis=1)
    w = 1.0 / np.sqrt(m * (81.0 - m))
    rng = np.random.default_rng(SEED)

    # Two readings per token: ink = black cells, and ink = white cells. Pixel-art communities
    # read both polarities and there is no on-chain fact that privileges one.
    rows = []
    nullcache = {}
    for idx, tid in enumerate(ids):
        for pol, vec in (("black", V[idx]), ("white", 1.0 - V[idx])):
            k = float(vec.sum())
            if k in (0.0, 81.0):
                continue
            s = scores(G, m, w, vec[None, :], np.array([k]))[:, 0]
            order = np.argsort(-s)[:3]
            if k not in nullcache:
                # The null depends on the grid only through k, so grids sharing a black
                # count share a null. That is not an approximation: permutations of any
                # 81-vector with k ones are identically distributed.
                nullcache[k] = best_null(G, m, w, int(k), rng)
            nd = nullcache[k]
            top = s[order[0]]
            p = (1.0 + (nd >= top).sum()) / (len(nd) + 1.0)
            rows.append({
                "id": tid, "polarity": pol, "black": meta[tid]["black"],
                "rarity": meta[tid]["rarity"], "owner": meta[tid]["owner"],
                "mcc": float(top), "p": float(p),
                "null_median": float(np.median(nd)), "null_max": float(nd.max()),
                "matches": [{"name": var[i]["name"], "kind": var[i]["kind"],
                             "fit": var[i]["fit"], "dx": var[i]["dx"], "dy": var[i]["dy"],
                             "aliases": var[i]["aliases"][:6], "mcc": float(s[i]),
                             "bits": var[i]["bits"]} for i in order],
            })

    rows.sort(key=lambda r: (r["p"], -r["mcc"]))
    json.dump({"nulls_per_grid": NULLS, "corpus_size": len(var), "seed": SEED,
               "rows": rows}, open("matches.json", "w"), indent=1)

    print(f"corpus {len(var)} distinct bitmaps, {NULLS} reshuffles per black-count, "
          f"{len(nullcache)} distinct black-counts")
    sig = [r for r in rows if r["p"] <= 0.05]
    print(f"{len(rows)} readings scored; {len(sig)} beat their own reshuffles at p<=0.05\n")
    print(f"{'tok':>4s} {'pol':<5s} {'blk':>3s} {'match':<12s} {'kind':<5s} "
          f"{'MCC':>6s} {'null med':>8s} {'p':>7s}")
    show = rows if "--all" in sys.argv else rows[:25]
    for r in show:
        b = r["matches"][0]
        print(f"{r['id']:>4s} {r['polarity']:<5s} {r['black']:>3d} "
              f"{b['name'] + ('@' + str(b['fit']) if b['fit'] != 9 else ''):<12s} "
              f"{b['kind']:<5s} {r['mcc']:6.3f} {r['null_median']:8.3f} {r['p']:7.4f}")


if __name__ == "__main__":
    main()
