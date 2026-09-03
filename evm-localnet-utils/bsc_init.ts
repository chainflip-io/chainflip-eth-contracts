#!/usr/bin/env -S pnpm tsx
// Copyright 2025 Chainflip Labs GmbH
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

import Web3 from 'web3';
import { setTimeout as sleep } from 'timers/promises';

const BSC_ENDPOINT = process.env.BSC_ENDPOINT ?? 'http://127.0.0.1:8645';
const BSC_ADDRESS_CHECKER =
  process.env.BSC_ADDRESS_CHECKER ??
  '0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0';

const DEPLOYER_PRIVATE_KEY =
  process.env.BSC_PRICE_FEED_DEPLOYER_PRIVATE_KEY ??
  '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80';
const DEPLOYER_ADDRESS = '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266';
const FIRST_PRICE_FEED_NONCE = 5;
const PRICE_FEED_DECIMALS = 8n;
const PRICE_FEED_DECIMAL_SCALE = 10n ** PRICE_FEED_DECIMALS;
const MIN_GAS_PRICE = 100_000_000n;
const DEPLOYMENT_GAS = 500_000;

const FEEDS = [
  {
    asset: 'BTC',
    description: 'BTC / USD',
    address: '0x5FC8d32690cc91D4c39d9d3abcBD16989F875707',
    price: 10_000n,
  },
  {
    asset: 'ETH',
    description: 'ETH / USD',
    address: '0x0165878A594ca255338adfa4d48449f69242Eb8F',
    price: 1_000n,
  },
  {
    asset: 'SOL',
    description: 'SOL / USD',
    address: '0xa513E6E4b8f2a923D98304ec87F64353C4D5C853',
    price: 100n,
  },
  {
    asset: 'USDC',
    description: 'USDC / USD',
    address: '0x2279B7A0a67DB372996a5FaB50D91eAA73d2eBe6',
    price: 1n,
  },
  {
    asset: 'USDT',
    description: 'USDT / USD',
    address: '0x8A791620dd6260079BF849Dc5567aDC3F2FdC318',
    price: 1n,
  },
  {
    asset: 'TRX',
    description: 'TRX / USD',
    address: '0x610178dA211FEF7D417bC0e6FeD39F05609AD788',
    price: 1n,
  },
  {
    asset: 'BNB',
    description: 'BNB / USD',
    address: '0xB7f8BC63BbcaD18155201308C8f3540b07f84F5e',
    price: 600n,
  },
  {
    asset: 'DOT',
    description: 'DOT / USD',
    address: '0xA51c1fc2f0D1a1b8494Ed1FE312d7C3a78Ed91C0',
    price: 10n,
  },
] as const;

const PRICE_FEED_ABI = [
  {
    inputs: [],
    name: 'decimals',
    outputs: [{ internalType: 'uint8', name: '', type: 'uint8' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [],
    name: 'description',
    outputs: [{ internalType: 'string', name: '', type: 'string' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [],
    name: 'latestRoundData',
    outputs: [
      { internalType: 'uint80', name: 'roundId', type: 'uint80' },
      { internalType: 'int256', name: 'answer', type: 'int256' },
      { internalType: 'uint256', name: 'startedAt', type: 'uint256' },
      { internalType: 'uint256', name: 'updatedAt', type: 'uint256' },
      { internalType: 'uint80', name: 'answeredInRound', type: 'uint80' },
    ],
    stateMutability: 'view',
    type: 'function',
  },
] as const;

const ADDRESS_CHECKER_ABI = [
  {
    inputs: [
      { internalType: 'address[]', name: 'addresses', type: 'address[]' },
    ],
    name: 'contractsDeployed',
    outputs: [{ internalType: 'bool[]', name: '', type: 'bool[]' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [
      { internalType: 'address[]', name: 'addresses', type: 'address[]' },
    ],
    name: 'queryPriceFeeds',
    outputs: [
      { internalType: 'uint256', name: 'blockNumber', type: 'uint256' },
      { internalType: 'uint256', name: 'blockTimestamp', type: 'uint256' },
      {
        components: [
          { internalType: 'uint80', name: 'roundId', type: 'uint80' },
          { internalType: 'int256', name: 'answer', type: 'int256' },
          { internalType: 'uint256', name: 'startedAt', type: 'uint256' },
          { internalType: 'uint256', name: 'updatedAt', type: 'uint256' },
          { internalType: 'uint80', name: 'answeredInRound', type: 'uint80' },
          { internalType: 'uint8', name: 'decimals', type: 'uint8' },
          { internalType: 'string', name: 'description', type: 'string' },
        ],
        internalType: 'struct IAddressChecker.PriceFeedData[]',
        name: '',
        type: 'tuple[]',
      },
    ],
    stateMutability: 'view',
    type: 'function',
  },
] as const;

// The BSC localnet image contains the core contracts but not Chainlink mock feeds.
// This deploys minimal localnet-only mocks with the read surface used by AddressChecker.
enum Opcode {
  ADD = 0x01,
  SUB = 0x03,
  EQ = 0x14,
  SHR = 0x1c,
  TIMESTAMP = 0x42,
  POP = 0x50,
  MSTORE = 0x52,
  SLOAD = 0x54,
  SSTORE = 0x55,
  JUMPI = 0x57,
  JUMPDEST = 0x5b,
  CALLDATALOAD = 0x35,
  CODECOPY = 0x39,
  DUP1 = 0x80,
  RETURN = 0xf3,
  REVERT = 0xfd,
}

class EvmAssembler {
  readonly bytes: number[] = [];
  private readonly labels = new Map<string, number>();
  private readonly patches: Array<{ label: string; offset: number }> = [];

  op(opcode: Opcode) {
    this.bytes.push(opcode);
  }

  label(name: string) {
    this.labels.set(name, this.bytes.length);
    this.op(Opcode.JUMPDEST);
  }

  pushNumber(value: bigint) {
    this.pushNumberWithWidth(value, Math.max(1, byteLength(value)));
  }

  pushBytes(bytes: number[]) {
    if (bytes.length < 1 || bytes.length > 32) {
      throw new Error(`Invalid PUSH width ${bytes.length}`);
    }
    this.bytes.push(0x5f + bytes.length, ...bytes);
  }

  pushHex(hex: string) {
    const cleaned = hex.replace(/^0x/, '');
    if (cleaned.length % 2 !== 0) {
      throw new Error(`Invalid hex string: ${hex}`);
    }
    this.pushBytes([...Buffer.from(cleaned, 'hex')]);
  }

  pushLabel(name: string) {
    this.bytes.push(0x61, 0xff, 0xff);
    this.patches.push({ label: name, offset: this.bytes.length - 2 });
  }

  build(): number[] {
    for (const patch of this.patches) {
      const value = this.labels.get(patch.label);
      if (value === undefined) {
        throw new Error(`Missing label ${patch.label}`);
      }
      if (value > 0xffff) {
        throw new Error(`Label ${patch.label} is too large: ${value}`);
      }
      this.bytes[patch.offset] = value >> 8;
      this.bytes[patch.offset + 1] = value & 0xff;
    }
    return this.bytes;
  }

  private pushNumberWithWidth(value: bigint, width: number) {
    if (value < 0n) {
      throw new Error(`Negative PUSH value ${value}`);
    }
    const hex = value.toString(16).padStart(width * 2, '0');
    this.pushBytes([...Buffer.from(hex, 'hex')]);
  }
}

function byteLength(value: bigint): number {
  if (value === 0n) return 1;
  return Math.ceil(value.toString(16).length / 2);
}

function pushFixedNumber(value: number, width: number): number[] {
  if (value < 0 || value >= 256 ** width) {
    throw new Error(`Value ${value} does not fit in ${width} bytes`);
  }
  return [
    0x5f + width,
    ...Buffer.from(value.toString(16).padStart(width * 2, '0'), 'hex'),
  ];
}

function pushNumber(value: bigint): number[] {
  return [0x5f + Math.max(1, byteLength(value)), ...numberBytes(value)];
}

function numberBytes(value: bigint): number[] {
  return [
    ...Buffer.from(
      value.toString(16).padStart(Math.max(1, byteLength(value)) * 2, '0'),
      'hex',
    ),
  ];
}

function buildRuntimeBytecode(description: string): number[] {
  const asm = new EvmAssembler();

  asm.pushNumber(0n);
  asm.op(Opcode.CALLDATALOAD);
  asm.pushNumber(224n);
  asm.op(Opcode.SHR);

  for (const [selector, label] of [
    ['0x313ce567', 'decimals'],
    ['0x54fd4d50', 'version'],
    ['0x7284e416', 'description'],
    ['0xfeaf968c', 'latestRoundData'],
    ['0xd4c19bda', 'updatePrice'],
  ] as const) {
    asm.op(Opcode.DUP1);
    asm.pushHex(selector);
    asm.op(Opcode.EQ);
    asm.pushLabel(label);
    asm.op(Opcode.JUMPI);
  }

  asm.pushNumber(0n);
  asm.pushNumber(0n);
  asm.op(Opcode.REVERT);

  asm.label('decimals');
  asm.pushNumber(8n);
  asm.pushNumber(0n);
  asm.op(Opcode.MSTORE);
  asm.pushNumber(32n);
  asm.pushNumber(0n);
  asm.op(Opcode.RETURN);

  asm.label('version');
  asm.pushNumber(6n);
  asm.pushNumber(0n);
  asm.op(Opcode.MSTORE);
  asm.pushNumber(32n);
  asm.pushNumber(0n);
  asm.op(Opcode.RETURN);

  asm.label('description');
  const descriptionBytes = Buffer.from(description, 'utf8');
  if (descriptionBytes.length > 32) {
    throw new Error(`Description is too long: ${description}`);
  }
  asm.pushNumber(32n);
  asm.pushNumber(0n);
  asm.op(Opcode.MSTORE);
  asm.pushNumber(BigInt(descriptionBytes.length));
  asm.pushNumber(32n);
  asm.op(Opcode.MSTORE);
  asm.pushHex(`0x${descriptionBytes.toString('hex').padEnd(64, '0')}`);
  asm.pushNumber(64n);
  asm.op(Opcode.MSTORE);
  asm.pushNumber(96n);
  asm.pushNumber(0n);
  asm.op(Opcode.RETURN);

  asm.label('latestRoundData');
  for (const [slot, offset] of [
    [0n, 0n],
    [1n, 32n],
    [2n, 64n],
    [3n, 96n],
    [4n, 128n],
  ] as const) {
    asm.pushNumber(slot);
    asm.op(Opcode.SLOAD);
    asm.pushNumber(offset);
    asm.op(Opcode.MSTORE);
  }
  asm.pushNumber(160n);
  asm.pushNumber(0n);
  asm.op(Opcode.RETURN);

  asm.label('updatePrice');
  asm.pushNumber(4n);
  asm.op(Opcode.CALLDATALOAD);
  asm.pushNumber(1n);
  asm.op(Opcode.SSTORE);

  asm.pushNumber(0n);
  asm.op(Opcode.SLOAD);
  asm.pushNumber(1n);
  asm.op(Opcode.ADD);
  asm.op(Opcode.DUP1);
  asm.pushNumber(0n);
  asm.op(Opcode.SSTORE);
  asm.pushNumber(4n);
  asm.op(Opcode.SSTORE);

  asm.op(Opcode.TIMESTAMP);
  asm.pushNumber(1n);
  asm.op(Opcode.SUB);
  asm.pushNumber(2n);
  asm.op(Opcode.SSTORE);

  asm.op(Opcode.TIMESTAMP);
  asm.pushNumber(3n);
  asm.op(Opcode.SSTORE);

  asm.op(Opcode.POP);
  asm.pushNumber(0n);
  asm.pushNumber(0n);
  asm.op(Opcode.RETURN);

  return asm.build();
}

function buildCreationBytecode(
  description: string,
  initialAnswer: bigint,
): string {
  const runtime = buildRuntimeBytecode(description);
  const constructor = [
    ...pushNumber(1n),
    ...pushNumber(0n),
    Opcode.SSTORE,
    ...pushNumber(initialAnswer),
    ...pushNumber(1n),
    Opcode.SSTORE,
    Opcode.TIMESTAMP,
    ...pushNumber(1n),
    Opcode.SUB,
    ...pushNumber(2n),
    Opcode.SSTORE,
    Opcode.TIMESTAMP,
    ...pushNumber(3n),
    Opcode.SSTORE,
    ...pushNumber(1n),
    ...pushNumber(4n),
    Opcode.SSTORE,
  ];
  const copyAndReturnLength = 15;
  const runtimeOffset = constructor.length + copyAndReturnLength;
  const copyAndReturn = [
    ...pushFixedNumber(runtime.length, 2),
    ...pushFixedNumber(runtimeOffset, 2),
    ...pushNumber(0n),
    Opcode.CODECOPY,
    ...pushFixedNumber(runtime.length, 2),
    ...pushNumber(0n),
    Opcode.RETURN,
  ];

  return `0x${Buffer.from([...constructor, ...copyAndReturn, ...runtime]).toString('hex')}`;
}

function isMissingCode(code: string): boolean {
  return code === '0x' || /^0x0+$/.test(code);
}

async function waitForRpc(web3: Web3) {
  for (let attempt = 0; attempt < 60; attempt++) {
    try {
      await web3.eth.net.isListening();
      return;
    } catch {
      await sleep(1_000);
    }
  }
  throw new Error(`BSC RPC did not become available at ${BSC_ENDPOINT}`);
}

async function main(): Promise<void> {
  const web3 = new Web3(BSC_ENDPOINT);
  await waitForRpc(web3);

  const checkerCode = await web3.eth.getCode(BSC_ADDRESS_CHECKER);
  if (isMissingCode(checkerCode)) {
    throw new Error(`BSC AddressChecker ${BSC_ADDRESS_CHECKER} has no code`);
  }

  const feedAddresses = FEEDS.map((feed) => feed.address);
  const codeByFeed = await Promise.all(
    feedAddresses.map((address) => web3.eth.getCode(address)),
  );
  const firstMissingFeedIndex = codeByFeed.findIndex(isMissingCode);

  if (firstMissingFeedIndex >= 0) {
    const missingAfterExistingFeed = codeByFeed
      .slice(firstMissingFeedIndex)
      .some((code) => !isMissingCode(code));
    if (missingAfterExistingFeed) {
      throw new Error('BSC price feed deployment is partial and non-contiguous');
    }

    const currentNonce = Number(
      await web3.eth.getTransactionCount(DEPLOYER_ADDRESS, 'latest'),
    );
    const expectedNonce = FIRST_PRICE_FEED_NONCE + firstMissingFeedIndex;
    if (currentNonce !== expectedNonce) {
      throw new Error(
        `Cannot deploy deterministic BSC price feeds: deployer nonce is ${currentNonce}, expected ${expectedNonce}`,
      );
    }

    const chainId = Number(await web3.eth.getChainId());
    const nodeGasPrice = BigInt(await web3.eth.getGasPrice());
    const gasPrice =
      nodeGasPrice > MIN_GAS_PRICE ? nodeGasPrice : MIN_GAS_PRICE;

    for (let i = firstMissingFeedIndex; i < FEEDS.length; i++) {
      const feed = FEEDS[i];
      const nonce = FIRST_PRICE_FEED_NONCE + i;
      const data = buildCreationBytecode(
        feed.description,
        feed.price * PRICE_FEED_DECIMAL_SCALE,
      );
      const signedTx = await web3.eth.accounts.signTransaction(
        {
          data,
          gas: DEPLOYMENT_GAS,
          gasPrice: gasPrice.toString(),
          nonce,
          chainId,
          value: '0',
        },
        DEPLOYER_PRIVATE_KEY,
      );
      const receipt = await web3.eth.sendSignedTransaction(
        signedTx.rawTransaction as string,
      );
      if (
        receipt.contractAddress?.toLowerCase() !== feed.address.toLowerCase()
      ) {
        throw new Error(
          `${feed.asset} price feed deployed at ${receipt.contractAddress}, expected ${feed.address}`,
        );
      }
      console.log(
        `Deployed BSC ${feed.description} price feed at ${receipt.contractAddress}`,
      );
    }
  } else {
    console.log('BSC price feeds already deployed');
  }

  for (const feed of FEEDS) {
    const priceFeed = new web3.eth.Contract(
      PRICE_FEED_ABI as never,
      feed.address,
    );
    const [description, decimals, latestRoundData] = await Promise.all([
      priceFeed.methods.description().call(),
      priceFeed.methods.decimals().call(),
      priceFeed.methods.latestRoundData().call(),
    ]);

    if (description !== feed.description) {
      throw new Error(
        `Unexpected BSC price feed description at ${feed.address}: ${description}, expected ${feed.description}`,
      );
    }
    if (BigInt(decimals) !== PRICE_FEED_DECIMALS) {
      throw new Error(
        `Unexpected BSC price feed decimals at ${feed.address}: ${decimals}, expected ${PRICE_FEED_DECIMALS}`,
      );
    }
    if (
      BigInt(latestRoundData.answer) <= 0n ||
      BigInt(latestRoundData.updatedAt) <= 0n
    ) {
      throw new Error(
        `BSC price feed ${feed.address} has invalid initial round data`,
      );
    }
  }

  const checker = new web3.eth.Contract(
    ADDRESS_CHECKER_ABI as never,
    BSC_ADDRESS_CHECKER,
  );
  const contractsDeployed = await checker.methods
    .contractsDeployed(feedAddresses)
    .call();
  if (!contractsDeployed.every(Boolean)) {
    throw new Error(
      `BSC AddressChecker did not see every price feed: ${contractsDeployed}`,
    );
  }

  const priceFeedQueryResult = await checker.methods
    .queryPriceFeeds(feedAddresses)
    .call();
  if (priceFeedQueryResult[2].length !== FEEDS.length) {
    throw new Error(
      `BSC AddressChecker returned ${priceFeedQueryResult[2].length} feeds, expected ${FEEDS.length}`,
    );
  }

  console.log('BSC price feeds are ready');
}

if (process.env.BSC_INIT_BUILD_ONLY === 'true') {
  for (const feed of FEEDS) {
    buildCreationBytecode(
      feed.description,
      feed.price * PRICE_FEED_DECIMAL_SCALE,
    );
  }
  console.log('BSC price feed creation bytecode built successfully');
} else {
  main().catch((error) => {
    console.error(error);
    process.exit(-1);
  });
}
