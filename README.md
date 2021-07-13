# Chainflip Ethereum Contracts

This repository contains the Ethereum smart contracts which are used to handle deposits and withdrawals based on signatures submitted via the vault nodes.

Additional information can be found in the [Ethereum Research](https://github.com/chainflip-io/ethereum-research) repository.

## Dependencies

- Python 2.7 or 3.5+
For Ubuntu `sudo apt-get install python3 python-dev python3-dev build-essential`
- [Poetry (Python dependency manager)](https://python-poetry.org/docs/)

## Usage

First, ensure you have Poetry installed.

```bash
git clone git@github.com:chainflip-io/chainflip-eth-contracts.git
cd chainflip-eth-contracts
poetry shell
poetry install
brownie pm install OpenZeppelin/openzeppelin-contracts@4.0.0
brownie test
```

### Generating Docs

Requires [Yarn](https://yarnpkg.com) and [NPX](https://www.npmjs.com/package/npx) to be installed.

```bash
yarn
npx solidity-docgen --solc-module solc-0.8
```

## Notes

Brownie and `solidity-docgen` don't play very nice with each other. For this reason we've installed the OpenZeppelin contracts through both the brownie package manager (because it doesn't like node_modules when compiling internally), and `yarn` (because `solc` doesn't search the `~/.brownie` folder for packages).

This isn't an ideal solution but it'll do for now.

## Deploy the contracts

The deploying account will be allocated all the FLIP on a testnet (90M)

Inside the poetry shell:

```bash
# ensure that the ETH account associated with this seed has ETH on that network
export SEED=<your seed phrase>
# deploy the contracts to rinkeby.
brownie run deploy_contracts --network rinkeby
```

## Useful commands

NB: You may need to run the tests with the additional `--network mainnet-fork`

`brownie test -s` - runs with the `print` outputs in tests. Currently there are only `print` outputs in the stateful test so one can visually verify that most txs are valid and not reverting

`brownie test --stateful false` runs all tests EXCEPT stateful tests

`brownie test --stateful true` runs ONLY the stateful tests
