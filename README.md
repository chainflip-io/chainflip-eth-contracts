# Chainflip Ethereum Contracts

This repository contains the Ethereum smart contracts which are used to handle deposits and withdrawals based on signatures submitted via the vault nodes.

Additional information can be found in the [Ethereum Research](https://github.com/chainflip-io/ethereum-research) repository.

## Dependencies

- Python 2.7 or 3.5+
For Ubuntu `sudo apt-get install python3 python-dev python3-dev build-essential`
- [Poetry (Python dependency manager)](https://python-poetry.org/docs/)

## Setup

First, ensure you have [Poetry](https://python-poetry.org) and [Yarn](https://yarnpkg.com) installed.

```bash
git clone git@github.com:chainflip-io/chainflip-eth-contracts.git
cd chainflip-eth-contracts
yarn
poetry shell
poetry install
brownie pm install OpenZeppelin/openzeppelin-contracts@4.0.0
```

Then, create a `.env` file using `.env.example` as a reference. ~~You will need an infura key to run the tests~~, and a seed to run the deploy script on a live network.

### Running Tests

We use the `hardhat` EVM for testing, since we use EIP1559 opcodes.

```bash
# Run without the stateful tests, because they take hours
brownie test --network hardhat --stateful false
```

### Generating Docs

Requires [Yarn](https://yarnpkg.com).

```bash
yarn docgen
```

## Notes

Brownie and `solidity-docgen` don't play very nice with each other. For this reason we've installed the OpenZeppelin contracts through both the brownie package manager (because it doesn't like node_modules when compiling internally), and `yarn` (because `solc` doesn't search the `~/.brownie` folder for packages).

This isn't an ideal solution but it'll do for now.

## Deploy the contracts

The deploying account will be allocated all the FLIP on a testnet (90M)

Inside the poetry shell:

### Local Test network

```bash
# if you haven't already started a hardhat node
npx hardhat node
# deploy the contracts - they will be deployed by acct #1 on the hardhat pre-seeded accounts
brownie run deploy_and
```

### Live Test network

```bash
# get this id from Infura
export WEB3_INFURA_PROJECT_ID=<Infura project id>
# ensure that the ETH account associated with this seed has ETH on that network
export SEED=<your seed phrase>
# Set an aggregate or governance key that you would like to use (optional)
export AGG_KEY=<agg key with leading parity byte, hex format, no leading 0x>
export GOV_KEY<gov key with leading parity byte, hex format, no leading 0x>
# Skip funding the contracts with 1 ETH when deploying
export SKIP_INITIAL_FUND=true

# deploy the contracts to rinkeby.
brownie run deploy_contracts --network rinkeby
```

## Useful commands

`brownie test -s` - runs with the `print` outputs in tests. Currently there are only `print` outputs in the stateful test so one can visually verify that most txs are valid and not reverting

`brownie test --stateful false` runs all tests EXCEPT stateful tests

`brownie test --stateful true` runs ONLY the stateful tests

`brownie run deploy_and all_events` will deploy the contracts and submit transactions which should emit the full suite of events
