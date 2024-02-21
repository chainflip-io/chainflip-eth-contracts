#!/usr/bin/env -S pnpm tsx
// INSTRUCTIONS
//
// This command takes no arguments.
// It will perform the initial arbitrum contract deployment according to the `arbRawDeploymentTxs.json` file
// and will send a transaction every ~260ms to mimic the Arbitrum mainnet block production.

import fs from 'fs/promises';
import Web3 from 'web3';
import { setTimeout as sleep } from 'timers/promises';

async function main(): Promise<void> {
  const web3 = new Web3(process.env.ARB_ENDPOINT ?? 'http://127.0.0.1:8547');
  const usdcArbitrumAddress = '0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9';

  const bytecode = await web3.eth.getCode(usdcArbitrumAddress);

  if (bytecode === '0x') {
    const abi = await fs.readFile('./commands/arbRawDeploymentTxs.json', 'utf-8');
    const arbRawTxs: JSON = JSON.parse(abi);

    // Loop through each raw transaction data
    for (const arbRawTx of Object.values(arbRawTxs)) {
      const txHash = await web3.eth.sendSignedTransaction(arbRawTx, (error) => {
        if (error) {
          console.log(`Arbitrum transaction failure:`, error);
        }
      });
      console.log(`Transaction sent with hash: ${txHash.transactionHash}`);
    }

    console.log('=== Arbitrum contracts deployed succesfully ===');
  } else {
    console.log(`=== Contracts already deployed ===`);
  }

  console.log('=== Start spamming ===');

  const whaleKey = '0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d';
  const whaleAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';

  // NOTE: The naive approach to just have a nonce increment every time seems to work fine
  let nonce = await web3.eth.getTransactionCount(whaleAddress);

  while (true) {
    const tx = { to: whaleAddress, data: undefined, gas: 5000000, nonce, value: 1 };

    const signedTx = await web3.eth.accounts.signTransaction(tx, whaleKey);

    await web3.eth.sendSignedTransaction(
      signedTx.rawTransaction as string,
      (error) => {
        if (error) {
          console.error(`Arbitrum transaction failure:`, error);
        }
      },
    );
    nonce++;
    await sleep(250);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(-1);
});
