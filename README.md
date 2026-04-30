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

### Tron compilation and test

```bash
yarn tronbox compile
# Test bytecode
node scripts/check_deposit_bytecode.js

# If using a `linux/arm64` you can start the tron node for testing like this:
docker run -d -p 9090:9090 tronbox/tre && sleep 5 && yarn tronbox test --network development

# Otherwise it needs some manual steps
docker build -t tron-base ci/docker/tron/
docker network create tron-net
docker run -d --name tron --network tron-net -p 8090:8090 -p 18888:18888 tron-base
docker run -d --name tron-peer --network tron-net tron-base -c /tron/config/config-peer.conf -d /tron/output-directory
sleep 5
# This runs all the migrations and then the tests
yarn tronbox test --network localnet

```

### Running Tests

We use the `tronbox` for testing.

```bash
yarn tronbox test --network localnet
```

### Linter

We use solhint and prettier for the solidity code and black for the python code. A general check is performed also in CI.

To run the lint check or to format the code, run the following inside the poetry shell:

```bash
poetry run yarn lint
poetry run yarn format
```

## Deploy the contracts

We want the live network contracts to match exactly the contracts in the localnet bytecode-wise. Otherwise the address derivation for deposit channels won't work. There is a small workaround for locally matching the CI deployment runs.

### Bytecode workaround

#### 1. Create the directory

```bash
# 1. Create the directory
sudo mkdir -p /opt/actions-runner/\_work/chainflip-eth-contracts

# 2. Copy the entire repo there (not symlink, not bind mount)
sudo cp -a /<local_path>/tron_contracts/chainflip-eth-contracts /opt/actions-runner/\_work/chainflip-eth-contracts/chainflip-eth-contracts

# 3. Make sure you own it
sudo chown -R $USER:$USER /opt/actions-runner/\_work/chainflip-eth-contracts/chainflip-eth-contracts

# 4. Go there and clean previous build artifacts
cd /opt/actions-runner/\_work/chainflip-eth-contracts/chainflip-eth-contracts
rm -rf build/contracts

# 5. Compile
yarn tronbox compile

# 6. Check compiled bytecode
node scripts/check_deposit_bytecode.js
```

### Local Test network

```bash
# It will use the default EVM deployer key and default endpoint
yarn tronbox migrate --f 1 --to 1 --reset --network localnet
```

### Live Test network

```bash
# It will use the default endpoint
export PRIVATE_KEY_NILE=<Tron private key>
yarn tronbox migrate --f 1 --to 1 --reset --network <nile/mainnet>
```

### Verify in Tronscan

https://developers.tron.network/docs/contract-verification
https://developers.tron.network/reference/flattening-your-contracts
https://support.tronscan.org/hc/en-us/articles/19500651417241-How-to-verify-contracts-with-subdirectory-structures
https://tronscan.org/#/contracts/verify

Identified the compiler version — checked tronbox.js: Solidity 0.8.20, optimizer enabled (800 runs), EVM istanbul, MIT License.

Flattened the contract cleanly using --silent to suppress yarn's banner:

```bash
yarn --silent tronbox flatten contracts/KeyManager.sol > KeyManager_flat.sol
```

Identified duplicate SPDX/pragma lines — the flattened file had 6 copies of each, which the Tron verifier rejects.
Deduplicated with a Python script, producing KeyManager_flat_clean.sol with exactly one SPDX-License-Identifier and one pragma solidity line. Python script:

```python
with open('KeyManager_flat.sol', 'r') as f:
    lines = f.readlines()

spdx_seen = False
pragma_seen = False
out = []
for line in lines:
    if 'SPDX-License-Identifier' in line:
        if spdx_seen:
            continue
        spdx_seen = True
    if line.startswith('pragma solidity'):
        if pragma_seen:
            continue
        pragma_seen = True
    out.append(line)

with open('KeyManager_flat_clean.sol', 'w') as f:
    f.writelines(out)
```

Maybe rename the obtained "KeyManager_flat_clean.sol" to something a bit nicer.
Uploaded to the Tron verifier — success.
