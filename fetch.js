#!/usr/bin/env node
/*
 * Read every Binary Pixels token straight off Base and write the 9x9 grids to grids.json.
 *
 * The whole piece lives on chain: tokenURI returns a base64 data URI whose "image" is a
 * base64 PNG of the 9x9 grid blown up to 900x900. No IPFS, no gateway, no API key. We keep
 * the PNG bytes so the grid can be re-derived by anyone, and decode the grid in Python.
 */
const fs = require("fs");
const { ethers } = require("/home/agent/work/wallet/node_modules/ethers");

const ADDR = "0x744D59F4F77E3556A62f51FfFAdD7A82859A3D38";
const ABI = [
  "function tokenURI(uint256) view returns (string)",
  "function totalSupply() view returns (uint256)",
  "function ownerOf(uint256) view returns (address)",
];

// A 29 KB return value is a large eth_call and public nodes drop them intermittently —
// measured here at roughly one failure in six per endpoint, uncorrelated between endpoints.
// So: rotate, and retry until every id has been either read or refused consistently.
const RPCS = [
  "https://mainnet.base.org",
  "https://base-rpc.publicnode.com",
  "https://1rpc.io/base",
];

(async () => {
  const provs = RPCS.map((u) => new ethers.JsonRpcProvider(u));
  const cs = provs.map((p) => new ethers.Contract(ADDR, ABI, p));
  const n = Number(await cs[0].totalSupply());
  const out = fs.existsSync("tokens.json")
    ? JSON.parse(fs.readFileSync("tokens.json", "utf8")) : {};

  for (let pass = 0; pass < 8; pass++) {
    const todo = [];
    // ids are 0-indexed: ownerOf(0) resolves, ownerOf(n) reverts.
    for (let i = 0; i < n; i++) if (!out[i]) todo.push(i);
    if (!todo.length) break;
    process.stderr.write(`pass ${pass}: ${todo.length} to fetch\n`);
    for (const i of todo) {
      const c = cs[(i + pass) % cs.length];
      try {
        const uri = await c.tokenURI(i);
        const owner = await c.ownerOf(i).catch(() => null);
        const j = JSON.parse(Buffer.from(uri.split(",")[1], "base64").toString());
        out[i] = { name: j.name, owner, attributes: j.attributes,
                   png_b64: j.image.split(",")[1] };
      } catch (e) { /* retried next pass against a different node */ }
    }
    fs.writeFileSync("tokens.json", JSON.stringify(out));
  }
  console.log(`${Object.keys(out).length} of ${n} tokens written to tokens.json`);
})();
