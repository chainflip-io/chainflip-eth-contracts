# Chainflip Ethereum Contracts

This repository contains the Ethereum smart contracts which are used to handle deposits and withdrawals based on signatures submitted via the vault nodes.

Additional information can be found in the [Ethereum Research](https://github.com/chainflip-io/ethereum-research) repository.


## Dependencies

- [Poetry (Python dependency manager)](https://python-poetry.org/docs/)


## Usage

First, ensure you have Poetry installed.

```
git clone git@github.com:chainflip-io/chainflip-eth-contracts.git
cd chainflip-eth-contracts
poetry shell
poetry install
brownie pm install OpenZeppelin/openzeppelin-contracts@3.3.0-solc-0.7
brownie test
```
