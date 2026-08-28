#!/usr/bin/env python3
"""What the p-value looks like if you forget you went looking.

Every reading in matches.json has a best shape, found by scoring the grid against 6,882 of
them. There are two ways to ask how surprising that match is:

  named-shape    "how often would a reshuffled grid match THIS shape as well?" -- the test
                 you are entitled to run if you named the shape before you looked.
  best-of-corpus "how often would a reshuffled grid match ANY of the 6,882 as well?" -- the
                 test you have to run if the shape is the one you found by looking.

The first has a closed form. For a fixed grid the MCC numerator collapses to 81a - mk, so
with m and k held fixed the score is monotone in the overlap a, and a under a uniform
reshuffle is exactly Hypergeometric(81, m, k). No simulation, no seed: the p is a sum of
binomial coefficients in exact integer arithmetic.

Which makes the comparison free across the whole collection, and that is the point. The
gap between the two columns is not a subtlety, it is the entire difference between a
collection full of discoveries and a collection of noise.

    python3 posthoc.py     # writes posthoc.json
"""
import json
from fractions import Fraction
from math import comb

N2 = 81


def p_named(m, k, a):
    """P(overlap >= a) for a uniformly random k-subset against a fixed m-subset of 81 cells."""
    hi = min(m, k)
    num = sum(comb(m, i) * comb(N2 - m, k - i) for i in range(a, hi + 1)
              if 0 <= k - i <= N2 - m)
    return float(Fraction(num, comb(N2, k)))


def main():
    grids = json.load(open("grids.json"))
    rows = json.load(open("matches.json"))["rows"]
    mine = json.load(open("mine.json"))

    out = []
    for r in rows:
        bits = "".join(grids[r["id"]]["rows"])
        if r["polarity"] == "white":
            bits = "".join("1" if c == "0" else "0" for c in bits)
        s = r["matches"][0]["bits"]
        k = sum(c == "1" for c in bits)
        m = sum(c == "1" for c in s)
        a = sum(x == "1" and y == "1" for x, y in zip(bits, s))
        out.append({"id": r["id"], "polarity": r["polarity"], "shape": r["matches"][0]["name"],
                    "mcc": r["mcc"], "p_best_of_corpus": r["p"],
                    "p_named_shape": p_named(m, k, a), "m": m, "k": k, "a": a})

    # Control: the same two numbers for #115 were also produced by 20,000 explicit
    # reshuffles in mine.py. If the closed form is right they agree to sampling error.
    check = []
    for rd in mine["readings"]:
        e = next(o for o in out if o["id"] == "115" and o["polarity"] == rd["polarity"])
        sim = rd["p_named_shape_posthoc"]
        se = (sim * (1 - sim) / mine["nulls"]) ** 0.5
        check.append({"polarity": rd["polarity"], "exact": e["p_named_shape"],
                      "simulated": sim, "draws": mine["nulls"],
                      "within_3se": abs(sim - e["p_named_shape"]) <= 3 * se + 1 / mine["nulls"]})
    assert all(c["within_3se"] for c in check), check

    n = len(out)
    named_sig = [o for o in out if o["p_named_shape"] <= 0.05]
    honest_sig = [o for o in out if o["p_best_of_corpus"] <= 0.05]
    both = [o for o in named_sig if o["p_best_of_corpus"] <= 0.05]
    ratios = sorted(o["p_best_of_corpus"] / o["p_named_shape"] for o in out
                    if o["p_named_shape"] > 0)
    med = sorted(o["p_named_shape"] for o in out)

    res = {"readings": n, "control": check,
           "named_significant": len(named_sig), "honest_significant": len(honest_sig),
           "both": len(both), "expected_at_5pct": round(0.05 * n, 1),
           "named_median_p": med[n // 2],
           "named_below_001": sum(o["p_named_shape"] <= 0.001 for o in out),
           "inflation_median": ratios[len(ratios) // 2],
           "rows": out}
    json.dump(res, open("posthoc.json", "w"), indent=1)

    print(f"{n} readings, 6,882 shapes each")
    for c in check:
        print(f"  control #115 {c['polarity']:<5s}: exact {c['exact']:.5f} vs "
              f"{c['simulated']:.5f} simulated ({c['draws']:,} draws) -> "
              f"{'agrees' if c['within_3se'] else 'DISAGREES'}")
    print(f"  named-shape p <= 0.05 : {len(named_sig):3d} of {n}  "
          f"({100 * len(named_sig) / n:.0f}%)   <- the test a holder would run by mistake")
    print(f"  named-shape p <= 0.001: {res['named_below_001']:3d} of {n}")
    print(f"  best-of-corpus <= 0.05: {len(honest_sig):3d} of {n}  "
          f"(chance predicts {res['expected_at_5pct']})")
    print(f"  median named-shape p  : {res['named_median_p']:.2e}, "
          f"median inflation {res['inflation_median']:.0f}x")


if __name__ == "__main__":
    main()
