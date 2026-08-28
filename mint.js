/* Mint one Binary Pixel through the collection's own mini app.
 *
 *   node mint.js         # price + preflight only, sends nothing
 *   node mint.js --send  # pay 0.0002 ETH, then ask the app to mint
 *
 * The app's flow, read out of its own bundle: send the quoted price as a plain
 * ETH transfer to the collection wallet, then POST the payment tx hash to
 * /api/nft/custom-mint, which mints to the address verified on the paying fid.
 * safeMint is owner-only on the contract, so this is the only way in — and it
 * is exactly what the mini app does when a human taps Mint.
 */
const fs = require('fs');
const { ethers } = require('/home/agent/work/wallet/node_modules/ethers');

const APP = 'https://miniapp-generator-fid-649360-260519085418859.neynar.app';
const SLUG = 'binary-pixels';
const FID = 3346381;
const PAYTO = '0x7c717EBb2f1a21124FC096E163981F02b940745f';   // collection wallet = contract owner
const NFT = '0x744D59F4F77E3556A62f51FfFAdD7A82859A3D38';
const MAX_PRICE_ETH = 0.001;   // refuse anything the app quotes above this

(async () => {
  const price = await (await fetch(`${APP}/api/nft/price?fid=${FID}&collectionSlug=${SLUG}&quantity=1`)).json();
  const supplyBefore = (await (await fetch(`${APP}/api/nft/total-supply?collectionSlug=${SLUG}`)).json()).total;
  const gas = await (await fetch(`${APP}/api/nft/gas-check`)).json();
  console.log('quoted price:', price.cost_eth, 'ETH | supply before:', supplyBefore, '| gas ok:', gas.ok);
  if (!(price.cost_eth > 0) || price.cost_eth > MAX_PRICE_ETH) throw new Error('price out of range');

  const provider = new ethers.JsonRpcProvider('https://mainnet.base.org', 8453, { staticNetwork: true });
  const key = JSON.parse(fs.readFileSync('/home/agent/work/wallet/keys.json', 'utf8')).privateKey;
  const wallet = new ethers.Wallet(key, provider);
  const bal = await provider.getBalance(wallet.address);
  const value = ethers.parseEther(price.cost_eth.toFixed(18));
  console.log('from:', wallet.address, '/', ethers.formatEther(bal), 'ETH | paying', ethers.formatEther(value));
  if (bal < value * 2n) throw new Error('balance too thin');

  if (!process.argv.includes('--send')) { console.log('\npreflight only — re-run with --send'); return; }

  const tx = await wallet.sendTransaction({ to: PAYTO, value });
  console.log('payment sent:', tx.hash);
  const rc = await tx.wait();
  console.log('mined in block', rc.blockNumber, 'status', rc.status);
  if (rc.status !== 1) throw new Error('payment reverted');

  const r = await fetch(`${APP}/api/nft/custom-mint`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fid: FID, collectionSlug: SLUG, paymentTxHash: tx.hash }),
  });
  const body = await r.json();
  console.log('custom-mint:', r.status, JSON.stringify(body).slice(0, 600));
  if (!r.ok || !body.tokens) throw new Error('mint failed');

  const nft = new ethers.Contract(NFT, ['function ownerOf(uint256) view returns (address)'], provider);
  for (const t of body.tokens) {
    const id = t.token_id;
    console.log('token', id, 'ownerOf ->', await nft.ownerOf(id));
  }
  fs.writeFileSync(__dirname + '/mint-result.json',
    JSON.stringify({ paymentTx: tx.hash, block: rc.blockNumber, price: price.cost_eth, tokens: body.tokens }, null, 2));
})().catch(e => { console.error('FAILED:', e.shortMessage || e.message); process.exit(1); });
