# Reproducible dev/deploy environment for chainflip-eth-contracts.
#
# Everything runs inside the pinned linux/amd64 image (see .devcontainer/Dockerfile)
# so that contract bytecode and CREATE/CREATE2 addresses are identical on every
# machine (incl. Mac M4) and match x64 CI/production.
#
#   make build            # build the image
#   make verify-bytecode  # PRIMARY determinism check (must pass; mirrors release CI)
#   make shell            # interactive shell in the container
#   make compile          # brownie compile
#   make test             # stateless test suite
#   make deploy           # deploy to an in-container hardhat node (local demo)
#   make deploy-eth       # deploy full suite to a throwaway eth localnet (chainId 10997)
#   make deploy-arb       # deploy full suite to a throwaway arb localnet (chainId 412346)
#   make deploy-bsc       # deploy full suite to a throwaway bsc localnet (chainId 343)
#   make deploy-all       # deploy-eth + deploy-arb + deploy-bsc
#   make deploy-summary   # print scripts/.artefacts/{eth,arb,bsc}.json
#   make deploy-live NETWORK=goerli   # deploy to a live network (needs .env + RPC)
#   make generate-verification-json CHAIN_ID=97   # Etherscan standard-json inputs
#                         #   for that chain's deployments recorded in build/deployments
#   make clean-build      # remove ./build (run once if you previously compiled
#                         #   outside this image, e.g. a native macOS brownie run)
#   make clean            # remove containers + named volumes
#
# The deploy-{eth,arb,bsc} targets each spin up a throwaway in-container hardhat node
# with the matching chainId, run the production `deploy_contracts` script, and print the
# deployed addresses. Same SEED + fresh chain + canonical bytecode => production
# addresses. Override any deploy var via .env or e.g. `make deploy-eth AGG_KEY=... SEED=...`.

COMPOSE := docker compose -f .devcontainer/docker-compose.yml
RUN := $(COMPOSE) run --rm dev
# Start a hardhat node in the background, wait for it, then run the given command.
WITH_NODE = bash -c 'npx hardhat node >/tmp/hardhat.log 2>&1 & until curl -s http://127.0.0.1:8545 >/dev/null; do sleep 1; done; $(1)'

# --- Deploy env (overridable). Test defaults mirror create-geth-arb-network.yml. -----
SEED                   ?= test test test test test test test test test test test junk
GOV_KEY                ?= 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266
COMM_KEY               ?= 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266
AGG_KEY                ?= 0331b2ba4b46201610901c5164f42edd1f64ce88076fde2e2c544f9dc3d7b350ae
GENESIS_STAKE          ?= 1000000000000000000000
NUM_GENESIS_VALIDATORS ?= 1
REDEMPTION_DELAY       ?= 120
DEPLOYER_ACCOUNT_INDEX ?= 0

DEPLOY_ENV := \
	-e SEED="$(SEED)" -e AGG_KEY="$(AGG_KEY)" -e GOV_KEY="$(GOV_KEY)" -e COMM_KEY="$(COMM_KEY)" \
	-e GENESIS_STAKE="$(GENESIS_STAKE)" -e NUM_GENESIS_VALIDATORS="$(NUM_GENESIS_VALIDATORS)" \
	-e REDEMPTION_DELAY="$(REDEMPTION_DELAY)" -e DEPLOYER_ACCOUNT_INDEX="$(DEPLOYER_ACCOUNT_INDEX)"

# $(1)=brownie network id  $(2)=chainId  $(3)=artefact id
define deploy_chain
	$(COMPOSE) run --rm $(DEPLOY_ENV) -e DEPLOY_ARTEFACT_ID=$(3) -e HH_CHAIN_ID=$(2) dev bash -c '\
		npx hardhat node --config hardhat.config.js >/tmp/hardhat.log 2>&1 & \
		until curl -s http://127.0.0.1:8545 >/dev/null; do sleep 1; done; \
		brownie networks delete $(1) 2>/dev/null || true; \
		brownie networks add Ethereum $(1) host=http://127.0.0.1:8545 chainid=$(2); \
		brownie run deploy_contracts --network $(1); \
		echo; echo "==== Deployed contracts ($(1), chainId $(2)) ===="; jq . scripts/.artefacts/$(3).json'
endef

.PHONY: build shell compile test verify-bytecode deploy deploy-eth deploy-arb deploy-bsc deploy-all deploy-summary deploy-live generate-verification-json clean-build clean

build:
	$(COMPOSE) build

shell:
	$(RUN) bash

compile:
	$(RUN) brownie compile

test:
	$(RUN) $(call WITH_NODE,brownie test --network hardhat --stateful false)

# Mirrors .github/workflows/release.yml — asserts the Deposit create2 addresses
# equal the canonical values in tests/shared_tests.py::deposit_bytecode_test.
verify-bytecode:
	$(RUN) $(call WITH_NODE,brownie test tests/unit/vault/test_deployAndFetchBatch.py::test_getCreate2Addr --network hardhat)

deploy:
	$(RUN) $(call WITH_NODE,brownie run deploy_and --network hardhat)

deploy-eth:
	$(call deploy_chain,eth-local,10997,eth)

deploy-arb:
	$(call deploy_chain,arb-local,412346,arb)

deploy-bsc:
	$(call deploy_chain,bsc-local,343,bsc)

deploy-all: deploy-eth deploy-arb deploy-bsc

deploy-summary:
	@for c in eth arb bsc; do \
		if [ -f scripts/.artefacts/$$c.json ]; then \
			echo "==== $$c ===="; jq . scripts/.artefacts/$$c.json; \
		else echo "==== $$c (not deployed) ===="; fi; \
	done

deploy-live:
	@test -n "$(NETWORK)" || { echo "Set NETWORK=<brownie-network>, e.g. make deploy-live NETWORK=goerli"; exit 1; }
	$(RUN) brownie run deploy_contracts --network $(NETWORK)

# CHAIN_ID selects which deployments to export from build/deployments/map.json;
# the script runs against a local hardhat node and never touches the live network.
generate-verification-json:
	@test -n "$(CHAIN_ID)" || { echo "Set CHAIN_ID=<chain id>, e.g. make generate-verification-json CHAIN_ID=97"; exit 1; }
	$(RUN) $(call WITH_NODE,brownie run generate_verification_json main $(CHAIN_ID) --network hardhat)

clean-build:
	rm -rf build

clean:
	$(COMPOSE) down -v
