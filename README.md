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

## Useful commands
`brownie test -s` - runs with the `print` outputs in tests. Currently there are only `print` outputs in the stateful test so one can visually verify that most txs are valid and not reverting

`brownie test --stateful false` runs all tests EXCEPT stateful tests

`brownie test --stateful true` runs ONLY the stateful tests


## Scripts

# !!!DON'T USE THE PRIVATE KEYS ASSOCIATED WITH THE MNEMONIC IN SCRIPTS ON MAINNET - YOU WILL LOSE YOUR ETH INSTANTLY!!!

The `testnet_and` script has some preset deploy and interaction functions for testing on testnets (currently only Ropsten has been set up). Deployment and fcns for interacting with existing deployments are separated in this script so that you can interact with existing contracts multiple times independently. You can run the following:

`brownie run testnet_and init_deploy --network ropsten` deploys new CF contracts. Note that other fcns like `stake_alice_and_bob` won't use these new addresses by default - you'd have to paste in the new addresses in the file
`brownie run testnet_and stake_alice_and_bob --network ropsten` creates 2 staking txs by 2 different stakers