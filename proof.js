/* Ownership proof for Binary Pixels #115, read live off Base.
 *
 *   node proof.js
 *
 * Writes proof.json and token-115.png. The PNG is the image out of the token's
 * own tokenURI, not a screenshot of a website: a screenshot proves what a server
 * said, and the point of an on-chain collection is that the chain says it.
 */
const fs = require('fs');
const crypto = require('crypto');
const { ethers } = require('/home/agent/work/wallet/node_modules/ethers');

const NFT = '0x744D59F4F77E3556A62f51FfFAdD7A82859A3D38';
const TID = 115;
const ME = '0x1C7afa67130ee637765a8281E83342E307409D57';
const RPCS = ['https://mainnet.base.org', 'https://base-rpc.publicnode.com', 'https://base.llamarpc.com'];

const ABI = ['function ownerOf(uint256) view returns (address)',
  'function tokenURI(uint256) view returns (string)',
  'function totalSupply() view returns (uint256)',
  'function name() view returns (string)'];

(async () => {
  const mint = JSON.parse(fs.readFileSync(__dirname + '/mint-result.json', 'utf8'));
  let provider;
  for (const url of RPCS) {
    try {
      provider = new ethers.JsonRpcProvider(url, 8453, { staticNetwork: true });
      await provider.getBlockNumber();
      break;
    } catch (e) { provider = null; }
  }
  if (!provider) throw new Error('no rpc');

  const c = new ethers.Contract(NFT, ABI, provider);
  const owner = await c.ownerOf(TID);
  if (owner.toLowerCase() !== ME.toLowerCase()) throw new Error('not mine: ' + owner);
  const uri = await c.tokenURI(TID);
  const supply = Number(await c.totalSupply());

  const meta = JSON.parse(Buffer.from(uri.split(',')[1], 'base64').toString('utf8'));
  const png = Buffer.from(meta.image.split(',')[1], 'base64');
  fs.writeFileSync(__dirname + '/token-115.png', png);

  // The payment and the mint are two transactions: I pay the collection wallet,
  // it mints to the address verified on my fid. Both are public.
  const pay = await provider.getTransactionReceipt(mint.paymentTx);
  const blk = await provider.getBlock(pay.blockNumber);
  const logs = await provider.getLogs({
    address: NFT, fromBlock: pay.blockNumber, toBlock: pay.blockNumber + 20,
    topics: [ethers.id('Transfer(address,address,uint256)'),
      ethers.zeroPadValue('0x0000000000000000000000000000000000000000', 32),
      ethers.zeroPadValue(ME, 32), ethers.zeroPadValue(ethers.toBeHex(TID), 32)],
  });
  if (logs.length !== 1) throw new Error('expected exactly one mint log, got ' + logs.length);
  const mtx = await provider.getTransactionReceipt(logs[0].transactionHash);

  const out = {
    contract: NFT, chain: 'base', chain_id: 8453, token: TID, owner,
    name: meta.name, attributes: meta.attributes, supply,
    token_uri_sha256: crypto.createHash('sha256').update(uri).digest('hex'),
    image_sha256: crypto.createHash('sha256').update(png).digest('hex'),
    image_bytes: png.length,
    payment: { tx: mint.paymentTx, block: pay.blockNumber, to: pay.to, from: pay.from,
      eth: mint.price, timestamp: blk.timestamp },
    mint: { tx: mtx.hash, block: mtx.blockNumber, from: mtx.from, log_index: logs[0].index },
  };
  fs.writeFileSync(__dirname + '/proof.json', JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out, null, 1).slice(0, 1200));
})().catch(e => { console.error('FAILED:', e.shortMessage || e.message); process.exit(1); });
