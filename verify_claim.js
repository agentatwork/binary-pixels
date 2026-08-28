/* Read the filed claim back off Base and write claim325-result.json.
 *
 * The claim id, the uri poidh will fetch, and the escrow holding the claim NFT are all
 * read from the chain rather than from the send script's console output, so the page
 * that quotes them cannot quote a claim that isn't there.
 */
const fs = require('fs');
const { ethers } = require('/home/agent/work/wallet/node_modules/ethers');

const POIDH = '0x5555fa783936c260f77385b4e153b9725fef1719';
const CLAIM_NFT = '0x27E117Cc9A8DA363442e7Bd0618939E3EEEACF6A';
const BOUNTY_ID = 325;
const ME = '0x1C7afa67130ee637765a8281E83342E307409D57';
const TX = '0x3c123276bdb591a50b9550807a74b271fc94a131185c3bf514b35cc0348e5b8f';

const ABI = ['function getClaimsByBountyId(uint256,uint256) view returns (tuple(uint256 id,address issuer,uint256 bountyId,address bountyIssuer,string name,string description,uint256 createdAt,bool accepted)[])'];
const NFT_ABI = ['function tokenURI(uint256) view returns (string)',
  'function ownerOf(uint256) view returns (address)'];

(async () => {
  const provider = new ethers.JsonRpcProvider('https://mainnet.base.org', 8453, { staticNetwork: true });
  const rc = await provider.getTransactionReceipt(TX);
  if (rc.status !== 1) throw new Error('claim tx did not succeed');

  const claims = await new ethers.Contract(POIDH, ABI, provider).getClaimsByBountyId(BOUNTY_ID, 0);
  const mine = claims.filter(c => c[6] !== 0n && c[1].toLowerCase() === ME.toLowerCase());
  if (mine.length !== 1) throw new Error('expected exactly one claim from me, got ' + mine.length);
  const c = mine[0];

  const nft = new ethers.Contract(CLAIM_NFT, NFT_ABI, provider);
  const out = {
    bounty: BOUNTY_ID, claim_id: Number(c[0]), tx: TX, block: rc.blockNumber,
    issuer: c[1], name: c[4], accepted: c[7],
    uri: await nft.tokenURI(c[0]),
    // v3 escrows the claim NFT in the bounty contract until the bounty settles.
    nft_contract: CLAIM_NFT, nft_held_by: await nft.ownerOf(c[0]),
    claims_on_bounty: claims.filter(x => x[6] !== 0n).length,
    description_chars: c[5].length,
  };
  fs.writeFileSync(__dirname + '/claim325-result.json', JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out, null, 1));
})().catch(e => { console.error('FAILED:', e.shortMessage || e.message); process.exit(1); });
