#!/usr/bin/env python3
"""Score token #115 — the one I minted — the same way as the other 115.

Two nulls, and they answer different questions:

  best-of-corpus   reshuffle the grid, take the best match over all 6,882 shapes, repeat.
                   This is the honest test for "I looked at everything and found a K",
                   because it charges me for the 6,882 chances I gave myself.

  named-shape      reshuffle the grid and score it against that one shape only. This is
                   the test you would run if you had named the shape BEFORE looking. I
                   did not, so it is reported as a diagnostic and labelled as one.

Writes mine.json.
"""
import json

import numpy as np

import match as M

TID = "115"
NULLS = 20000
SEED = 20260828


def main():
    var, G = M.load_corpus()
    grids = json.load(open("grids.json"))
    meta = grids[TID]
    bits = "".join(meta["rows"])
    m = G.sum(axis=1)
    w = 1.0 / np.sqrt(m * (81.0 - m))
    rng = np.random.default_rng(SEED)

    out = {"id": TID, "name": meta["name"], "owner": meta["owner"], "black": meta["black"],
           "rarity": meta["rarity"], "rows": meta["rows"], "corpus": len(var),
           "nulls": NULLS, "seed": SEED, "readings": []}

    for pol in ("black", "white"):
        vec = np.array([[int(c) for c in bits]], dtype=np.float32)
        if pol == "white":
            vec = 1.0 - vec
        k = float(vec.sum())
        s = M.scores(G, m, w, vec, np.array([k]))[:, 0]
        order = np.argsort(-s)[:10]

        # best-of-corpus null
        nd = M.best_null(G, m, w, int(k), rng, reps=NULLS)
        top = float(s[order[0]])
        p_best = float((1.0 + (nd >= top).sum()) / (NULLS + 1.0))

        # named-shape null for the top shape only, same reshuffles' worth of draws
        base = np.zeros(81, dtype=np.float32)
        base[: int(k)] = 1.0
        j = int(order[0])
        named = np.empty(NULLS, dtype=np.float32)
        for a in range(0, NULLS, 2000):
            b = min(a + 2000, NULLS)
            block = np.stack([rng.permutation(base) for _ in range(b - a)])
            named[a:b] = M.scores(G[j: j + 1], m[j: j + 1], w[j: j + 1], block,
                                  np.full(b - a, k))[0]
        p_named = float((1.0 + (named >= top).sum()) / (NULLS + 1.0))

        out["readings"].append({
            "polarity": pol, "k": int(k), "mcc": top,
            "p_best_of_corpus": p_best, "p_named_shape_posthoc": p_named,
            "null_median": float(np.median(nd)), "null_p95": float(np.quantile(nd, 0.95)),
            "top": [{"name": var[i]["name"], "kind": var[i]["kind"], "fit": var[i]["fit"],
                     "dx": var[i]["dx"], "dy": var[i]["dy"], "mcc": float(s[i]),
                     "aliases": var[i]["aliases"][:6], "bits": var[i]["bits"]} for i in order],
            "best_by_kind": {kind: max(
                ({"name": var[i]["name"], "fit": var[i]["fit"], "mcc": float(s[i]),
                  "bits": var[i]["bits"], "dx": var[i]["dx"], "dy": var[i]["dy"]}
                 for i in range(len(var)) if var[i]["kind"] == kind),
                key=lambda d: d["mcc"]) for kind in ("font", "cjk", "drawn")},
        })

    # collection-wide refresh, so the page's context numbers come from the same run
    rows = json.load(open("matches.json"))["rows"]
    sig = [r for r in rows if r["p"] <= 0.05]
    out["collection"] = {"tokens": len(grids), "readings": len(rows), "significant": len(sig),
                         "expected_at_5pct": round(0.05 * len(rows), 1),
                         "significant_ids": [f'#{r["id"]} {r["polarity"]}' for r in sig]}
    json.dump(out, open("mine.json", "w"), indent=1)

    for r in out["readings"]:
        t = r["top"][0]
        print(f'{r["polarity"]:<6s} k={r["k"]:>2d} best {t["name"]!r}@{t["fit"]} '
              f'MCC {r["mcc"]:.3f} | p(best-of-corpus) {r["p_best_of_corpus"]:.4f} '
              f'| p(named, post hoc) {r["p_named_shape_posthoc"]:.4f} '
              f'| null median {r["null_median"]:.3f}')
        for kind, b in r["best_by_kind"].items():
            print(f'    best {kind:<5s} {b["name"]!r}@{b["fit"]} {b["mcc"]:.3f}')
    print(out["collection"])


if __name__ == "__main__":
    main()
