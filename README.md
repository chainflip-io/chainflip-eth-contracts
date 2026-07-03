# Chainflip Ethereum Contracts

This repository contains the set of Ethereum smart contracts used in the Chainflip protocol. It also contains tests and deployment scripts.

## Overview

Chainflip is a cross-chain decentralised exchange, coordinated through its own blockchain, referred to as the Chainflip State Chain. The State Chain is a proof of stake application-specfic blockchain that requires the FLIP token to be staked.

The State Chain Gatway contract holds the FLIP funds that are being used to stake to the State Chain. The Vault contract holds the funds used for the exchange functionality of the protocol. The State Chain nodes have control over the funds held in these contracts via a threshold signature scheme. The KeyManager is the contract storing all the necessary keys and performing signature verification.

## Reproducible builds with the dev container

Contract bytecode is **not** environment-independent. `solc` embeds a CBOR metadata hash at the end of every contract's bytecode, and that hash includes the compiler's `settings.remappings`. Brownie resolves the OpenZeppelin remapping to an **absolute** path under `$HOME/.brownie`, so the value of `$HOME` — along with the CPU architecture, the `solc`/OpenZeppelin/brownie versions, and the path the repo lives at — leaks into every contract's bytecode and therefore into the deterministic `CREATE2` deposit addresses. A native build on a Mac (arm64, `$HOME=/Users/you`) will produce different bytecode than an x64 CI/production build, which breaks address parity.

To make builds **byte-identical on every machine** (including Apple Silicon) and match x64 CI/production, this repo ships a pinned dev container under [`.devcontainer/`](.devcontainer/). It neutralises all per-machine variation by fixing:

- **platform** → `linux/amd64` (emulated on Apple Silicon via Docker Desktop),
- **`$HOME`** → `/home/ubuntu` (matches the CI/production build host),
- **repo path** → `/opt/chainflip-eth-contracts` (fixed canonical mount point),
- **toolchain** → `solc` 0.8.20, OpenZeppelin 4.8.3, `eth-brownie` 1.18.2, Poetry 2.2.1, Node 18 (all pinned via lockfiles).

A CI job ([`verify-bytecode-parity.yml`](.github/workflows/verify-bytecode-parity.yml)) compiles the contracts both natively and inside this container and diffs every contract's bytecode to prove they are identical.

There are two ways to work inside the container:

- **`make shell`** — opens an interactive shell inside the container with the full toolchain (`brownie`, `slither`, `yarn`, …) on `PATH`. Every command snippet in this README is meant to be run here.
- **VS Code Dev Containers** — open the repo and choose "Reopen in Container" (see [`.devcontainer/devcontainer.json`](.devcontainer/devcontainer.json)) to get the same shell in a VS Code terminal.

The `make` targets below are convenience wrappers that run individual commands inside the container for you (build, test, deploy) without opening a shell.

### Requirements

The only host dependencies are:

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose (Docker Desktop on Mac/Windows includes both),
- `make`.

Everything else (Python 3.9, Poetry, Node/yarn, `solc`, brownie packages, OpenZeppelin) is baked into the image.

## Make commands

All targets run inside the pinned dev container. Run `make build` once first to build the image.

| Command | Description |
| --- | --- |
| `make build` | Build the pinned `linux/amd64` dev-container image. |
| `make shell` | Open an interactive shell inside the container (for ad-hoc `brownie`, `slither`, `yarn`, etc.). |
| `make compile` | `brownie compile`. |
| `make test` | Run the stateless test suite (`brownie test --network hardhat --stateful false`) against an in-container hardhat node. |
| `make verify-bytecode` | **Primary determinism check.** Asserts the `Deposit` `CREATE2` addresses equal the canonical values in `tests/shared_tests.py`. Mirrors the release CI. |
| `make deploy` | Deploy to an in-container hardhat node (local demo). |
| `make deploy-eth` | Deploy the full suite to a throwaway eth localnet (chainId 10997). |
| `make deploy-arb` | Deploy the full suite to a throwaway arb localnet (chainId 412346). |
| `make deploy-bsc` | Deploy the full suite to a throwaway bsc localnet (chainId 343). |
| `make deploy-all` | `deploy-eth` + `deploy-arb` + `deploy-bsc`. |
| `make deploy-summary` | Print the deployed addresses from `scripts/.artefacts/{eth,arb,bsc}.json`. |
| `make deploy-live NETWORK=goerli` | Deploy to a live network (needs `.env` + RPC endpoint). |
| `make clean-build` | Remove `./build` (run once if you previously compiled outside the container, e.g. a native macOS brownie run). |
| `make clean` | Remove the containers and named volumes. |

The `deploy-{eth,arb,bsc}` targets each spin up a throwaway in-container hardhat node with the matching chainId, run the production `deploy_contracts` script, and print the deployed addresses. Same `SEED` + a fresh chain + canonical bytecode ⇒ the production addresses. Deploy variables (`SEED`, `AGG_KEY`, `GOV_KEY`, `COMM_KEY`, `GENESIS_STAKE`, `NUM_GENESIS_VALIDATORS`, …) default to the test values in the `Makefile` and can be overridden via `.env` or on the command line, e.g. `make deploy-eth AGG_KEY=... SEED=...`.

## Setup

```bash
git clone git@github.com:chainflip-io/chainflip-eth-contracts.git
cd chainflip-eth-contracts
make build
```

Then, set the appropriate environment variables. See `.env.example` as an example — the container reads `.env` automatically. To deploy on a live network a SEED and an RPC endpoint is needed.

### Running Tests

We use the `hardhat` EVM for testing.

Launch a container shell with `make shell` (or open a terminal inside the VS Code Dev Container), then run:

```bash
# Run without the stateful tests, because they take hours
poetry run brownie test --network hardhat --stateful false
```

Run tests with additional features. Inside the same container shell:

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

> Note: brownie needs a hardhat node. Inside the container shell start one first with `npx hardhat node &`. (The `make test` wrapper does this for you.)

### Static Analysis

Slither is used for static analysis. In the event of the command below failing, try removing the `build/` directory (`make clean-build`) and run it again.

Inside a container shell (`make shell`, or a VS Code Dev Container terminal):

```bash
slither .
```

### Linter

We use solhint and prettier for the solidity code and black for the python code. A general check is performed also in CI.

Inside a container shell (`make shell`, or a VS Code Dev Container terminal), run the following to lint the check or to format the code:

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

Current pre-commit hooks implemented:

- lint

To perform a commit without running the pre-commits, add the --no-verify flag to the git commit command. (not recommended)

## Deploy the contracts

The deploying account will be allocated all the FLIP on a testnet (90M).

### Local Test network

Launch a container shell with `make shell` (or open a terminal inside the VS Code Dev Container), then run:

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

As a shortcut, `make deploy` runs the hardhat node + `deploy_and` for you, and `make deploy-eth` / `deploy-arb` / `deploy-bsc` reproduce the full production deployment (and canonical `CREATE2` addresses) against throwaway localnets with the right chainId.

### Live Test network

Launch a container shell with `make shell` (or open a terminal inside the VS Code Dev Container), then run:

```bash
# get this id from Infura and/or Alchemy
export WEB3_INFURA_PROJECT_ID=<Infura project id>
export WEB3_ALCHEMY_PROJECT_ID=<Infura project id>
# ensure that the ETH account associated with this seed has ETH on that network
export SEED="<your seed phrase>"
# Set an aggregate key, a governance address and a community address that you would like to use
export AGG_KEY=<agg key with leading parity byte, hex format, no leading 0x>
export GOV_KEY=<gov address, hex format, with leading 0x>
export COMM_KEY=<comm address, hex format, with leading 0x>
# Set genesis parameters
export GENESIS_STAKE=<the stake each node should have at genesis> (default =
50000000000000000000000)
export NUM_GENESIS_VALIDATORS=<number of genesis validators in the chainspec you expect to start against this contract> (default = 5)

# deploy the contracts to goerli.
poetry run brownie run deploy_contracts --network goerli
```

Alternatively, put the same variables in `.env` and run `make deploy-live NETWORK=goerli` from the host.

## Useful commands

Inside a container shell (`make shell`, or a VS Code Dev Container terminal):

`poetry run brownie test -s` - runs with the `print` outputs in tests. Currently there are only `print` outputs in the stateful test so one can visually verify that most txs are valid and not reverting

`poetry run brownie test --stateful false` runs all tests EXCEPT stateful tests

`poetry run brownie test --stateful true` runs ONLY the stateful tests
