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

Run tests with additional features:

```bash
brownie test --network hardhat --stateful <BOOL> --coverage --gas --hypothesis-seed <SEED>
```
Flags:
- `--stateful <BOOL>` - Runs (or not) stateful tests. Stateful tests might take several hours so it is recommended to set it to false.
- `--gas` - generates a gas profile report
- `--coverage` - generates and updates the test coverage report under reports/coverage.json
- `--hypothesis-seed <SEED>` - Inputs a seed (int) to the hypothesis strategies. Useful to deterministically reproduce tests failures and for accurate gas comparisons when doing gas optimizations.

### Linter

We use solhint and prettier for the solidity code and black for the python code. A general check is performed also in CI.

To locally do a general check on both solidity and python code:

```bash
yarn lint
```

Format the solidity code using solhint+prettier:

```bash
yarn format-sol
```

Format the python code using black:

```bash
yarn format-py
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
export GENESIS_STAKE=<the stake each node should have at genesis> (default = 500000000000000000000000)
export NUM_GENESIS_VALIDATORS=<number of genesis validators in the chainspec you expect to start against this contract> (default = 5)

# deploy the contracts to rinkeby.
brownie run deploy_contracts --network rinkeby
```

## Useful commands

`brownie test -s` - runs with the `print` outputs in tests. Currently there are only `print` outputs in the stateful test so one can visually verify that most txs are valid and not reverting

`brownie test --stateful false` runs all tests EXCEPT stateful tests

`brownie test --stateful true` runs ONLY the stateful tests

`brownie run deploy_and all_events` will deploy the contracts and submit transactions which should emit the full suite of events
