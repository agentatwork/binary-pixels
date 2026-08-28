/* Submit the Binary Pixels #115 claim to poidh bounty #325 on Base.
 *
 *   node claim325.js          # encode, simulate, print — sends nothing
 *   node claim325.js --send   # actually broadcast
 *
 * The uri is a metadata JSON with an "image" key, not a bare PNG: poidh renders the
 * claim card by fetching the uri and reading .image, so pointing it straight at an
 * image gives every viewer a blank card.
 */
const fs = require('fs');
const { ethers } = require('/home/agent/work/wallet/node_modules/ethers');

const RPCS = ['https://mainnet.base.org', 'https://base-rpc.publicnode.com'];
const POIDH = '0x5555fa783936c260f77385b4e153b9725fef1719';
const BOUNTY_ID = 325;                 // on-chain id; poidh.xyz calls this 1311

const NAME = 'There is a K in my grid, and I put it there';
const URI = 'https://agentatwork.xyz/notes/binary-pixels-115-card.json';
const DESCRIPTION = fs.readFileSync(__dirname + '/claim325.txt', 'utf8').trim();

const ABI = ['function createClaim(uint256 bountyId, string name, string description, string uri)',
  'function bounties(uint256) view returns (uint256 id, address issuer, string name, string description, uint256 amount, address claimer, uint256 createdAt, uint256 claimId)'];

(async () => {
  let provider, lastErr;
  for (const url of RPCS) {
    try {
      provider = new ethers.JsonRpcProvider(url, 8453, { staticNetwork: true });
      await provider.getBlockNumber();
      console.log('rpc:', url);
      break;
    } catch (e) { lastErr = e; provider = null; }
  }
  if (!provider) throw lastErr;

  const key = JSON.parse(fs.readFileSync('/home/agent/work/wallet/keys.json', 'utf8')).privateKey;
  const wallet = new ethers.Wallet(key, provider);
  const poidh = new ethers.Contract(POIDH, ABI, wallet);

  // Claiming a bounty that is already paid out, or a different bounty than intended,
  // costs the same gas as claiming the right one. Read it back first.
  const b = await poidh.bounties(BOUNTY_ID);
  console.log('bounty', b[0].toString() + ':', JSON.stringify(b[2]));
  console.log('  amount', ethers.formatEther(b[4]), 'ETH | claimer', b[5]);
  if (b[5] !== ethers.ZeroAddress) throw new Error('already claimed by ' + b[5]);

  const bal = await provider.getBalance(wallet.address);
  console.log('from:', wallet.address, '/', ethers.formatEther(bal), 'ETH');
  console.log('description:', DESCRIPTION.length, 'chars | uri', URI);

  const data = poidh.interface.encodeFunctionData('createClaim',
    [BOUNTY_ID, NAME, DESCRIPTION, URI]);
  console.log('calldata:', (data.length - 2) / 2, 'bytes, selector', data.slice(0, 10));

  await provider.call({ to: POIDH, from: wallet.address, data });
  console.log('eth_call simulation: ok (would not revert)');

  const gas = await provider.estimateGas({ to: POIDH, from: wallet.address, data });
  const fee = await provider.getFeeData();
  const maxFee = fee.maxFeePerGas ?? fee.gasPrice;
  const cost = gas * maxFee;
  console.log('gas:', gas.toString(), '| max cost:', ethers.formatEther(cost), 'ETH');
  if (cost > bal) throw new Error('insufficient balance for gas');

  if (!process.argv.includes('--send')) {
    console.log('\ndry run — nothing sent. Re-run with --send to broadcast.');
    return;
  }

  const tx = await poidh.createClaim(BOUNTY_ID, NAME, DESCRIPTION, URI,
    { gasLimit: (gas * 13n) / 10n });
  console.log('sent:', tx.hash);
  const rc = await tx.wait();
  console.log('mined in block', rc.blockNumber, '| status', rc.status,
    '| gas used', rc.gasUsed.toString());
  console.log('https://basescan.org/tx/' + tx.hash);
})().catch(e => { console.error('FAILED:', e.shortMessage || e.message); process.exit(1); });
