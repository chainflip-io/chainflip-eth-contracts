# Chainflip Ethereum Contracts

This repository contains the set of Ethereum smart contracts used in the Chainflip protocol. It also contains tests and deployment scripts.

## Overview

Chainflip is a cross-chain decentralised exchange, coordinated through its own blockchain, referred to as the Chainflip State Chain. The State Chain is a proof of stake application-specfic blockchain that requires the FLIP token to be staked.

The State Chain Gatway contract holds the FLIP funds that are being used to stake to the State Chain. The Vault contract holds the funds used for the exchange functionality of the protocol. The State Chain nodes have control over the funds held in these contracts via a threshold signature scheme. The KeyManager is the contract storing all the necessary keys and performing signature verification.

## Dependencies

- Python >3.7, <3.10
  For Ubuntu `sudo apt-get install python3 python-dev python3-dev build-essential`
- [Poetry (Python dependency manager)](https://python-poetry.org/docs/) v2.2.1

In case of python version dependency issues it might be useful to use a virtual environment such as pyenv. For example:

```bash
pyenv install 3.8.10
poetry env use ~/.pyenv/versions/3.8.10/bin/python
poetry install
```

## Setup

First, ensure you have [Poetry](https://python-poetry.org), [Yarn](https://yarnpkg.com) and Ganache (`npm install -g ganache-cli`) are installed.

```bash
git clone git@github.com:chainflip-io/chainflip-eth-contracts.git
cd chainflip-eth-contracts
yarn
poetry shell
poetry install
poetry run brownie pm install OpenZeppelin/openzeppelin-contracts@4.8.3
# optional
pre-commit install
```

Then, set the appropriate environment variables. See `.env.example` as an example. To deploy on a live network a SEED and an RPC endpoint is needed.

### Running Tests

We use the `hardhat` EVM for testing.

```bash
# Run without the stateful tests, because they take hours
poetry run brownie test --network hardhat --stateful false
```

Run tests with additional features:

```bash
poetry run brownie test <test-name> -s --network hardhat --stateful <bool> --coverage --gas --hypothesis-seed <seed_number>
```

Flags:

- `<test-name>` - Run a specific test. If no test-name is provided all tests are run.
- `-s`- Runs with the `print` outputs in tests.
- `--stateful <bool>` - Runs (or not) stateful tests. Stateful tests might take several hours so it is recommended to set it to false.
- `--gas` - generates a gas profile report
- `--coverage` - generates and updates the test coverage report under reports/coverage.json
- `--hypothesis-seed <seed_number>` - Inputs a seed (int) to the hypothesis strategies. Useful to deterministically reproduce tests failures and for accurate gas comparisons when doing gas optimizations.

### Static Analysis

Slither is used for static analysis. In the event of the command below failing, try removing the `build/` directory and run it again.

Inside the poetry shell:

```bash
slither .
```

### Linter

We use solhint and prettier for the solidity code and black for the python code. A general check is performed also in CI.

To run the lint check or to format the code, run the following inside the poetry shell:

```bash
poetry run yarn lint
poetry run yarn format
```

## Fuzzing

Echidna is used for fuzzing the contracts. Make sure to follow Echidna's installation instructions or simply download the compiled binary. For Ubuntu:

```bash
curl -fL https://github.com/crytic/echidna/releases/download/v2.0.2/echidna-test-2.0.2-Ubuntu-18.04.tar.gz -o echidna-test-2.0.2-Ubuntu-18.04.tar.gz
tar -xvf echidna-test-2.0.2-Ubuntu-18.04.tar.gz
```

Make sure solc is installed with the latest versions with support to at least Solidity 0.8.0. To install:

`sudo snap install solc --edge`

Then Echidna can be run as normal. Echidna is not capable of reading the inherited contracts from packages under node_modules and needs an extra remapping in the config files. So always specify one of the echidna.config.yml files. There are different configuration files that can be specified for the different test modes.

```bash
./echidna-test contracts/echidna/tests/TestEchidna.sol --contract TestEchidna --config contracts/echidna/tests/echidna-assertion.config.yml
```

### Pre-commit hook

Pre-commit is part of the poetry virtual environment. Therefore, ensure that poetry is installed when commiting.

Current pre-commit hooks implemented:

- lint

To perform a commit without running the pre-commits, add the --no-verify flag to the git commit command. (not recommended)

## Deploy the contracts

The deploying account will be allocated all the FLIP on a testnet (90M)

Inside the poetry shell:

### Local Test network

```bash
# if you haven't already started a hardhat node
npx hardhat node
# Instead, to run with interval mining - so the node continues mining blocks periodically
npx hardhat node --config hardhat-interval-mining.config.js
# If brownie fails to connect to the hardhat node check ip and run with the adequate hostname address. For instance:
npx hardhat node --hostname 127.0.0.1
# deploy the contracts - they will be deployed by acct #1 on the hardhat pre-seeded accounts
poetry run brownie run deploy_contracts
```

### Live Test network

The script automatically detects whether to run an Ethereum or secondary EVM deployment (Arbitrum, BNB) based on the chain ID. Ethereum requires extra parameters due to the staking contract.

**All networks:**

```bash
# get this id from Infura and/or Alchemy
export WEB3_INFURA_PROJECT_ID=<Infura project id>
export WEB3_ALCHEMY_PROJECT_ID=<Alchemy project id>
# ensure that the ETH account associated with this seed has ETH on that network
export SEED="<your seed phrase>"
# Set an aggregate key, a governance address and a community address that you would like to use
export AGG_KEY=<agg key with leading parity byte, hex format, no leading 0x>
export GOV_KEY=<gov address, hex format, with leading 0x>
export COMM_KEY=<comm address, hex format, with leading 0x>
```

**Ethereum only**:

```bash
# Set genesis parameters
export GENESIS_STAKE=<the stake each node should have at genesis> (default = 50000000000000000000000)
export NUM_GENESIS_VALIDATORS=<number of genesis validators in the chainspec you expect to start against this contract> (default = 5)
export REDEMPTION_DELAY=<redemption delay in seconds>
```

```bash
# deploy the contracts to Sepolia.
poetry run brownie run deploy_contracts --network sepolia
```

### Gas estimations

The simplest way to run gas estimations locally for the main Vault AllBatch transaction is to run:

```bash
poetry run brownie test tests/unit/vault/test_allBatch_gas.py --network hardhat --stateful false --gas
```

Some EVM networks differ on gas costs. Also, the localnet hardhat node might differ from the real live network due to different configuration, fork etc.. The same tests can be run on a live network. Make sure to set the `SEED` environment and the endpoint rpc environment.

```bash
poetry run brownie test tests/unit/vault/test_allBatch_gas.py --network sepolia --stateful false --gas
```

### Bytecode

#### CBOR Metadata Hash and Absolute Paths

Solidity appends a CBOR-encoded blob to the end of every compiled contract's bytecode. This blob contains a hash of the compiler metadata, which includes source file paths. Brownie records **absolute paths** to source files in that metadata. This means the CBOR hash and therefore the deployed bytecode changes. The bytecode of the Deposit contract that is embedded into the Vault contract is used in address derivation in the State Chain, which means this directly impact deposit channel address generation.

To reproduce and/or deploy byte-for-byte identical bytecode to what CI compiles and what is deployed on live networks, the project must be compiled from `/home/ubuntu/`. Follow the steps below on a Linux machine.

#### Reproducing CI/Mainnet Bytecode

```bash
# 1. Create the expected directory and take ownership
sudo mkdir /home/ubuntu && sudo chown -R $USER:$USER /home/ubuntu

# 2. Clone the repo directly into /home/ubuntu
cd /home/ubuntu
git clone git@github.com:chainflip-io/chainflip-eth-contracts.git
mv chainflip-eth-contracts/* .
mv chainflip-eth-contracts/.[!.]* . 2>/dev/null || true
rm -rf chainflip-eth-contracts/

# 3. Install dependencies
yarn
poetry shell
poetry install
```

Verify compilation is reproducible by running a test that checks bytecode (it should fail at this point because the OpenZeppelin remapping still points to the wrong path):

```bash
poetry run brownie test tests/unit/vault/test_deployAndFetchBatch.py::test_getCreate2Addr --network hardhat
```

#### Fixing the OpenZeppelin Remapping

Brownie resolves OpenZeppelin imports via a remapping in its compiler module. By default this remapping uses the path `~/.brownie/packages/...`, which expands to your actual home directory rather than `/home/ubuntu`. You must patch it manually.

Patch the `_get_solc_remappings` function in the Brownie compiler module to hardcode the `/home/ubuntu` path:

```bash
sed -i 's|.*return \[f.*remapped_dict.*|    return ["@openzeppelin=/home/ubuntu/.brownie/packages/OpenZeppelin/openzeppelin-contracts@4.8.3"]|' \
  "$(poetry env list --full-path | head -1)/lib/python3.8/site-packages/brownie/project/compiler/__init__.py"
```

#### Providing the OpenZeppelin Package

Rather than downloading the package via Brownie's package manager (which would place it under your real home), copy it directly from `node_modules`:

```bash
mkdir -p /home/ubuntu/.brownie/packages/OpenZeppelin/openzeppelin-contracts@4.8.3
cp -r node_modules/@openzeppelin/contracts /home/ubuntu/.brownie/packages/OpenZeppelin/openzeppelin-contracts@4.8.3/
```

#### Recompile and Verify

```bash
rm -rf build
poetry run brownie compile
poetry run brownie test tests/unit/vault/test_deployAndFetchBatch.py::test_getCreate2Addr --network hardhat
```

The test should now pass, and the compiled bytecode will match what CI and mainnet produced.

> **Note:** Stripping the CBOR suffix from the bytecode would make compilation environment-independent, but Etherscan and other block explorers rely on it to verify and display contract source code. For this reason we keep it and control the compilation path instead.

> **Note:** An alternative is to pull the `build/` artifacts from CI and deploy without recompiling (either by pre-populating `build/` and getting Brownie to not recompile, or by manually crafting deployment transactions with the known bytecode). However, both of those options are prone to human error.

## Useful commands

`poetry run brownie test -s` - runs with the `print` outputs in tests. Currently there are only `print` outputs in the stateful test so one can visually verify that most txs are valid and not reverting

`poetry run brownie test --stateful false` runs all tests EXCEPT stateful tests

`poetry run brownie test --stateful true` runs ONLY the stateful tests
