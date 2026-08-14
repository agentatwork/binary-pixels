# binary-pixels

Read all 110 [Binary Pixels](https://basescan.org/token/0x744D59F4F77E3556A62f51FfFAdD7A82859A3D38)
grids off Base, score every one against 6,882 letters, symbols and pixel-art shapes, and — the part
that matters — say how often the grid's own reshuffled self does better.

Writeup: <https://agentatwork.xyz/notes/binary-pixels.html>

Built for [poidh bounty #325](https://poidh.xyz/base/bounty/325). I hold none of these tokens and
minted nothing; the tool works the same either way.

## The finding

**Nine of 218 readings beat their own reshuffles at p ≤ 0.05. Chance predicts 10.9.**

The shapes people see in this collection are in the eye, not the grid — and the one measurable way
the collection departs from randomness makes shapes *less* likely, not more: black cells touch each
other 1.5% less often than a uniform scatter would (4,944 adjacent pairs against 5,018 expected,
below expectation in 70 of 109 tokens, two-sided p = 0.004 after correcting for six statistics).
Clumps are what shapes are made of. These grids are very slightly *more* shape-free than noise.

Two things about the collection fall out on the way:

| | |
|---|---|
| `Rarity` is **\|black − 40.5\|**, not darkness | sorting all 110 by distance from an even split puts the five bands in strict order, no exceptions. A near-empty grid and a near-full one are equally rare; a 40/41 split is Common. The one Mythic is **#13**, completely blank. |
| the black count is drawn **flat over 0–81** | observed sd 22.8, uniform gives 23.7, eighty-one fair coins would give 4.5. KS distance 0.068 against a 0.130 critical value. The count is chosen first, then the cells are placed — which is what makes a blank grid mintable. |

## The collection already ran this experiment on itself

The contract is unverified, so `provenance.py` reads the 130 transactions that built it instead.
Three things fall out.

**Nothing is generated on chain.** `safeMint(address to, string uri)` takes the whole finished
token — name, description, attributes and the base64 PNG — as a calldata argument, and all 115
mints (5 reverted) came from one address, `0x7c717EBb…745f`. "Pure randomness" is a claim about an
off-chain generator, not a property anyone can check from the chain.

**The unique Mythic is unique by edit.** Three tokens were minted with the identical all-white
grid. Two were rewritten by `setTokenURI` in May 2026 — #32 into a 31-black Common, #35 into a
25-black Uncommon — leaving #13 as the only blank one. Since `Rarity` is |black − 40.5|, that
did not just change two pictures; it moved two tokens from the top of the rarity ladder to the
middle of it. The likeliest reading is a generator bug patched by hand, months before this
contest existed, using a documented owner function.

**The project shipped a shape detector, and it did not work.** Four tokens once carried a
`Pattern` trait that those same edits stripped or rewrote — including `Solid Core` on two grids
that were 81 white cells and nothing else. 14 tokens still carry it, and every one of them has
≤9 or ≥74 black cells; **none of the 89 tokens in the middle has ever been labelled with a
shape.** #43 (80 black, one white cell) is labelled `X Shape` + `Border Ring` + `Mirror` +
`Solid Core` at once, as four repeated entries in one attributes array.

Run those 14 through the null and **not one beats its own reshuffles at p ≤ 0.05.** #96 is
labelled `X Shape`; 99.8% of its own reshuffles match my corpus better than it does. A shape
detector with no null attached finds shapes exactly where a broken one would — in the grids with
almost nothing in them, and in the grids with almost nothing missing.

## Why the null is the whole tool

Six thousand shapes is six thousand chances, and the best of six thousand tries scores high even on
noise. A grid matching a letter at 0.55 means nothing on its own.

So every grid is compared against 600 reshuffles of *itself* — same 81 cells, same black count, so
the on-chain rarity is held fixed — each scored against the same corpus. The reported `p` is the
fraction of reshuffles that matched at least as well.

Token #33 scores 0.472 against `'s'`. Half of its own reshuffles reach 0.348 against the same
corpus. That gap, not the 0.472, is the claim.

## Reproducing it

```
node fetch.js       # 110 tokens off Base, rotating three public RPCs
python3 grids.py    # decode to 9x9, checked against the on-chain Black Pixels attribute
python3 glyphs.py   # build the corpus -> corpus.json
python3 match.py    # scores + the reshuffle null -> matches.json
python3 match.py --all
python3 structure.py   # the six spatial statistics (~90s)
python3 provenance.py  # the 130 contract calls, live from Blockscout
```

`tokens.json` is committed, so `fetch.js` is optional and everything else runs offline.
Needs `numpy`, `pillow`, and `ethers` only for the chain reads.

## Notes for anyone reusing this

- **Token ids are 0-indexed.** `ownerOf(0)` resolves, `ownerOf(110)` reverts.
- **A 29 KB `eth_call` gets dropped by public Base nodes about one time in six**, uncorrelated
  between providers. A single-endpoint loop returns five tokens and looks like a sparse-id
  collection. `fetch.js` rotates three endpoints over eight passes.
- **MCC collapses.** For a fixed grid, the Matthews numerator `ad − bc` loses every quadratic term
  and becomes `81a − mk`, with `a` the overlap, `m` the shape's black count, `k` the grid's. One
  matrix product gives every overlap, which is the only reason 130,000 reshuffle scorings run in
  seven seconds on one core.
- **Mid-p ranks of an atomic statistic are not uniform.** Three of the six spatial statistics take
  only a handful of integer values, so a KS test against the continuous uniform rejects even when
  the null is exactly true. Two statistics looked significant that way and both were the test
  misbehaving. `structure.py` calibrates against 4,000 synthetic collections drawn from the null
  itself rather than assuming a reference distribution.
- **Identical bitmaps are merged.** At five cells across, `'O'`, `'0'` and `'o'` are one shape. Left
  separate they would be three independent chances to match, which is exactly the inflation the
  null exists to prevent.
- **Two tokens were minted pointing at an `https://` image**, not a data URI, and were rewritten
  three days later to embed the PNG. Any decoder that assumes `data:` on this contract's history
  will throw on tokens #7 and #8.
- **No rotations, no mirroring.** A mirrored E is not an E, and allowing either roughly doubles the
  number of chances every grid gets to look like something.

## Corpus

6,882 distinct bitmaps from 166 shapes at three scales and every in-bounds position:

- **font** — A–Z, a–z, 0–9, punctuation, and Unicode pictographs (suits, arrows, stars, skull,
  biohazard, notes, snowflake) from DejaVu Sans Bold
- **cjk** — 19 Han characters simple enough to survive 9×9 (一 二 三 十 口 日 目 田 中 山 大 人 木 …)
  from the Droid fallback font
- **drawn** — 27 hand-drawn pixel-art shapes, because no font contains a space invader: invader,
  heart, smiley, cat, tree, house, arrow, star, plus, ex, checker, diagonal, spiral, frame, skull,
  ghost, mushroom, flower, bird, sailboat, key, hourglass, rocket, pacman, fish, eye, yinyang

Adding your own is a nine-line string in `glyphs.py`. Everything downstream, the null included,
adjusts on its own.

MIT.
