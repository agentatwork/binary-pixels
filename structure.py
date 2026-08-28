#!/usr/bin/env python3
"""What generated these grids?

Three questions, answered from the grids alone (the contract is unverified on
Blockscout, so there is no source to read):

  1. How is the Rarity trait assigned? The black counts inside each rarity band overlap
     heavily, so it is not a threshold on the count itself.
  2. How is the black count chosen? It is nowhere near Binomial(81, 1/2), which is what
     flipping 81 fair coins would give.
  3. Given the count, is there any spatial structure -- do black cells clump, touch,
     mirror, line up? This is the question that decides whether pareidolia in this
     collection can be real, because a grid with no spatial structure beyond its count
     is, by construction, a uniformly random k-subset of the 81 cells.

Question 3 is tested against the exact same permutation null match.py uses, which is not
a coincidence: if the answer is "no structure", then that null is not an approximation of
the generator, it *is* the generator.
"""
import json

import numpy as np

SEED = 20260814
REPS = 20000


def stats(a):
    """Spatial summaries of a 9x9 grid, each one a way a shape could show up."""
    return np.array([
        (a[:, :-1] & a[:, 1:]).sum() + (a[:-1] & a[1:]).sum(),  # touching black pairs
        (a == a[:, ::-1]).sum(),                                # left-right symmetry
        (a == a[::-1]).sum(),                                   # top-bottom symmetry
        (a == a.T).sum(),                                       # diagonal symmetry
        max(a.sum(0).max(), a.sum(1).max()),                    # longest filled row/col
        (a[:-1, :-1] & a[:-1, 1:] & a[1:, :-1] & a[1:, 1:]).sum(),  # solid 2x2 blocks
    ], dtype=np.float64)


NAMES = ["adjacent black pairs", "mirror-symmetric cells", "flip-symmetric cells",
         "transpose-symmetric cells", "longest full row/col", "solid 2x2 blocks"]


def main():
    g = json.load(open("grids.json"))
    ids = sorted(g, key=int)
    A = np.array([[[int(c) for c in r] for r in g[i]["rows"]] for i in ids], dtype=np.int64)
    k = A.reshape(len(ids), -1).sum(1)
    rng = np.random.default_rng(SEED)

    print("=== 1. the Rarity trait ===")
    # Every band's count range straddles 40.5, so try distance from a perfectly balanced grid.
    d = np.abs(k - 40.5)
    for r in ["Mythic", "Legendary", "Rare", "Uncommon", "Common"]:
        m = np.array([g[i]["rarity"] == r for i in ids])
        if not m.any():
            continue
        print(f"  {r:<9s} n={m.sum():3d}  black {k[m].min():2d}..{k[m].max():2d}  "
              f"|black - 40.5| in {d[m].min():5.1f}..{d[m].max():5.1f}")
    order = np.argsort(d)
    lab = [g[ids[i]]["rarity"] for i in order]
    clean = all(["Common", "Uncommon", "Rare", "Legendary", "Mythic"].index(lab[i]) <=
                ["Common", "Uncommon", "Rare", "Legendary", "Mythic"].index(lab[i + 1])
                for i in range(len(lab) - 1))
    print(f"  sorting all {len(ids)} by |black - 40.5| puts the bands in strict order: "
          f"{'yes' if clean else 'no'}")
    print("  -> Rarity measures imbalance, not darkness. A near-empty grid and a near-full")
    print("     grid are equally rare; a 40/41 split is Common.")

    print("\n=== 2. the black count ===")
    print(f"  observed  mean {k.mean():5.2f}  sd {k.std(ddof=1):5.2f}  "
          f"range {k.min()}..{k.max()}")
    print(f"  81 fair coin flips would give mean 40.50  sd  4.50  range about 26..55")
    u = np.sqrt((82 ** 2 - 1) / 12)
    print(f"  uniform over 0..81 gives      mean 40.50  sd {u:5.2f}  range  0..81")
    # Kolmogorov-Smirnov against the discrete uniform on 0..81.
    x = np.sort(k)
    emp = np.arange(1, len(x) + 1) / len(x)
    ks = max(np.abs(emp - (x + 1) / 82).max(), np.abs((x) / 82 - (emp - 1 / len(x))).max())
    print(f"  KS distance from uniform(0..81): {ks:.3f}  "
          f"(5% critical value at n={len(k)} is {1.36 / np.sqrt(len(k)):.3f})")
    print("  -> the count is drawn flat across the whole range, then the cells are filled.")
    print("     That is a deliberate choice: it is what makes an all-white grid mintable.")

    print("\n=== 3. spatial structure, given the count ===")
    print("  For each token, compare it to 20,000 reshuffles of its own cells. If the")
    print("  generator picks a count and then scatters that many black cells uniformly,")
    print(f"  every z below is noise around zero and the sum over {len(ids)} tokens is too.")
    obs = np.array([stats(a) for a in A])
    keep = (k > 0) & (k < 81)
    cache = {}
    for kk in sorted({int(x) for x in k[keep]}):
        base = np.zeros(81, dtype=np.int64)
        base[:kk] = 1
        cache[kk] = np.array([stats(rng.permutation(base).reshape(9, 9)) for _ in range(REPS)])

    def midp(null, v):
        """Rank of v among the null draws, splitting ties. Excludes v itself if present."""
        s = np.sort(null, axis=0)
        lo = np.array([np.searchsorted(s[:, j], v[j], "left") for j in range(len(v))])
        hi = np.array([np.searchsorted(s[:, j], v[j], "right") for j in range(len(v))])
        return (lo + 0.5 * (hi - lo)) / len(null)

    ps = np.full_like(obs, np.nan)
    for i in np.where(keep)[0]:
        ps[i] = midp(cache[int(k[i])], obs[i])

    # Calibrate the whole procedure against itself. Three of these statistics take only a
    # handful of integer values -- a grid has 0, 1 or 2 solid 2x2 blocks and rarely more --
    # and the mid-p of an atomic statistic is not uniform on (0,1), it is a few spikes. A
    # KS test against the continuous uniform therefore rejects even when the null is exactly
    # true, which is a property of the test and not a fact about the collection. So instead
    # of assuming a reference distribution, build one: draw a synthetic collection of
    # scorable grids from the null itself, with the same black counts, push it through the identical
    # mid-p machinery, and see where the real collection falls among 4,000 of those.
    selfp = {kk: np.stack([midp(np.delete(v, r, axis=0), v[r]) for r in range(400)])
             for kk, v in cache.items()}
    sim = np.empty((4000, len(NAMES)))
    for t in range(4000):
        sim[t] = np.mean([selfp[int(k[i])][rng.integers(400)] for i in np.where(keep)[0]], axis=0)

    pvals = {}
    print(f"\n  {'statistic':<26s} {'mean p':>7s} {'null mean p':>12s} {'2-sided':>8s} "
          f"{'low':>4s} {'high':>4s}")
    for j, nm in enumerate(NAMES):
        o = ps[keep, j].mean()
        c = sim[:, j]
        pv = 2 * min((c <= o).mean(), (c >= o).mean())
        pvals[nm] = float(min(pv, 1.0))
        star = "  <--" if pv < 0.05 / len(NAMES) else ""
        print(f"  {nm:<26s} {o:7.3f} {c.mean():9.3f}+-{c.std():.3f} {min(pv, 1.0):8.4f} "
              f"{int((ps[keep, j] < 0.025).sum()):4d} {int((ps[keep, j] > 0.975).sum()):4d}{star}")
    print("\n  Column 2 is where an unstructured collection lands, measured rather than assumed.")
    print(f"  Column 3 is two-sided against that. With six statistics the 5% line is "
          f"{0.05 / len(NAMES):.4f}.")

    # The adjacency figures the writeup quotes, computed here rather than typed there.
    adj = int(obs[keep, 0].sum())
    exp = float(sum(cache[int(k[i])][:, 0].mean() for i in np.where(keep)[0]))
    below = int(sum(obs[i, 0] < cache[int(k[i])][:, 0].mean() for i in np.where(keep)[0]))
    print(f"\n  adjacent black pairs: {adj} observed against {exp:.0f} expected "
          f"({100 * (adj - exp) / exp:+.1f}%), below expectation in {below} of {int(keep.sum())}")

    json.dump({"ids": ids, "black": k.tolist(), "reps": REPS, "scorable": int(keep.sum()),
               "pvals": pvals, "bonferroni": 0.05 / len(NAMES),
               "ks": float(ks), "ks_crit": float(1.36 / np.sqrt(len(k))),
               "rarity_strict_order": bool(clean),
               "adjacency": {"observed": adj, "expected": exp, "below": below},
               "p": {NAMES[j]: ps[:, j].tolist() for j in range(len(NAMES))},
               "null_mean_p": {NAMES[j]: [float(sim[:, j].mean()), float(sim[:, j].std())]
                               for j in range(len(NAMES))}},
              open("structure.json", "w"))


if __name__ == "__main__":
    main()
