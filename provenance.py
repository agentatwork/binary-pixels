#!/usr/bin/env python3
"""Where do these grids actually come from?

The contract is unverified, so the only way to answer is to read the calls that made it.
`safeMint(address to, string uri)` takes the entire token metadata -- name, description,
attributes, and the base64 PNG of the 9x9 grid -- as a calldata argument. The grid is not
generated on chain and not derived from any chain value: it arrives finished, written by
whoever sent the transaction.

That is worth establishing precisely rather than asserting, because it decides what the
word "random" can mean for this collection, and because the same read turns up the
`setTokenURI` calls, which are the interesting part.

Writes provenance.json and prints the summary. Uses Blockscout's free API, no key.
"""
import base64
import collections
import json
import subprocess
import time
import urllib.parse

CONTRACT = "0x744D59F4F77E3556A62f51FfFAdD7A82859A3D38"
API = f"https://base.blockscout.com/api/v2/addresses/{CONTRACT}/transactions?filter=to"


def get(url):
    for attempt in range(4):
        r = subprocess.run(["curl", "-sS", "-H", "User-Agent: Mozilla/5.0", url],
                           capture_output=True, text=True)
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            time.sleep(1 + attempt)
    raise RuntimeError(f"no JSON from {url}")


def decode_uri(u):
    """data:application/json;base64,... -> the parsed metadata."""
    if not u.startswith("data:application/json;base64,"):
        return None
    return json.loads(base64.b64decode(u.split(",", 1)[1]))


def grid_of(meta):
    """The 9x9 grid as a string of 81 characters, sampled from the PNG.

    Returns None when the image is not embedded. Two tokens were minted pointing at an
    https:// host instead of a data URI, so this is a real case and not defensive padding.
    """
    import io

    import numpy as np
    from PIL import Image
    src = meta.get("image", "")
    if not src.startswith("data:image/"):
        return None
    im = Image.open(io.BytesIO(base64.b64decode(src.split(",", 1)[1])))
    a = np.asarray(im.convert("L"))
    step = a.shape[0] // 9
    g = a[step // 2::step, step // 2::step][:9, :9]
    return "".join("1" if v == 0 else "0" for v in g.ravel())


def main():
    txs, nxt = [], None
    while True:
        d = get(API + ("&" + urllib.parse.urlencode(nxt) if nxt else ""))
        if not d.get("items"):
            break
        txs.extend(d["items"])
        nxt = d.get("next_page_params")
        if not nxt:
            break
        time.sleep(0.4)

    mints, edits, senders = {}, [], collections.Counter()
    fails = []
    for t in txs:
        di = t.get("decoded_input") or {}
        call = di.get("method_call", "")
        p = {x["name"]: x["value"] for x in di.get("parameters", [])}
        if call.startswith("safeMint"):
            senders[t["from"]["hash"]] += 1
            if t.get("status") != "ok":
                fails.append(t["hash"])
                continue
            m = decode_uri(p.get("uri", ""))
            if m:
                mints[m["name"]] = {"meta": m, "to": p.get("to"),
                                    "ts": t.get("timestamp"), "hash": t["hash"]}
        elif call.startswith("setTokenURI"):
            edits.append({"tokenId": p.get("_tokenId"), "meta": decode_uri(p.get("_newURI", "")),
                          "ts": t.get("timestamp"), "hash": t["hash"],
                          "status": t.get("status")})

    print(f"{len(txs)} transactions to the contract")
    print(f"  safeMint      {sum(senders.values()):3d}  from {len(senders)} address(es), "
          f"{len(fails)} reverted")
    for a, c in senders.most_common():
        print(f"                     {a}  x{c}")
    print(f"  setTokenURI   {len(edits):3d}")
    print("\nEvery token's image, name, description and attributes arrive as a calldata")
    print("argument. Nothing about the pattern is computed on chain or derived from any")
    print("chain value, so 'pure randomness' is a claim about an off-chain generator, not")
    print("a property anyone can verify from the contract.")

    print(f"\n=== the {len(edits)} setTokenURI calls ===")
    changed = []
    for e in sorted(edits, key=lambda x: str(x["ts"])):
        tid, m = e["tokenId"], e["meta"]
        if not m:
            print(f"  token {tid}: uri not a data URI")
            continue
        orig = mints.get(m["name"])
        row = {"tokenId": tid, "name": m["name"], "ts": e["ts"], "status": e["status"]}
        if orig is None:
            print(f"  token {tid} -> {m['name']}: no matching mint found")
            changed.append(row)
            continue
        a, b = grid_of(orig["meta"]), grid_of(m)
        diff = None if a is None or b is None else sum(x != y for x, y in zip(a, b))
        aa = {x["trait_type"]: x["value"] for x in orig["meta"]["attributes"]}
        bb = {x["trait_type"]: x["value"] for x in m["attributes"]}
        row.update({"cells_changed": diff, "before": aa, "after": bb,
                    "image_was": "off-chain url" if a is None else "embedded png",
                    "image_now": "off-chain url" if b is None else "embedded png",
                    "before_grid": a, "after_grid": b})
        changed.append(row)
        d = "n/a" if diff is None else f"{diff:2d}"
        note = "" if a is not None else "   (was an https:// image, now embedded)"
        drop = set(aa) - set(bb)
        print(f"  #{str(tid):<3s} {e['ts'][:10]}  cells changed: {d}   "
              f"black {aa.get('Black Pixels'):>2} -> {bb.get('Black Pixels'):>2}   "
              f"{str(aa.get('Rarity')):<9s} -> {str(bb.get('Rarity')):<9s}"
              f"{'   dropped ' + ','.join(sorted(drop)) if drop else ''}{note}")

    json.dump({"contract": CONTRACT, "tx_count": len(txs),
               "mint_senders": dict(senders), "reverted_mints": fails,
               "edits": changed}, open("provenance.json", "w"), indent=1)


if __name__ == "__main__":
    main()
