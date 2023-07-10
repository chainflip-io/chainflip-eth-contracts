import sys
import os
import json

sys.path.append(os.path.abspath("tests"))
from consts import *
from utils import prompt_user_continue_or_break
from brownie import (
    chain,
    accounts,
    KeyManager,
    Vault,
    StateChainGateway,
    FLIP,
    MockUSDC,
    DeployerContract,
    CFReceiverMock,
    AddressChecker,
)
from deploy import (
    deploy_Chainflip_contracts,
    deploy_usdc_contract,
    deploy_new_cfReceiverMock,
    deploy_contracts_secondary_evm,
)

AUTONOMY_SEED = os.environ["SEED"]
DEPLOY_ARTEFACT_ID = os.environ.get("DEPLOY_ARTEFACT_ID")
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)
deployer = cf_accs[DEPLOYER_ACCOUNT_INDEX]
print(f"DEPLOYER = {deployer}")


def main():
    if chain.id in arbitrum_networks:
        deploy_secondary_evm()
    else:
        # Default to deploying all the contracts
        deploy_ethereum()


def deploy_ethereum():
    check_env_variables(
        [
            "REDEMPTION_DELAY",
            "GENESIS_STAKE",
            "NUM_GENESIS_VALIDATORS",
        ]
    )

    # For live deployment, add a confirmation step to allow the user to verify the parameters.
    if chain.id == eth_mainnet:
        # Print all the environment variables for mainnet deployment.
        print("\nTo be deployed with parameters\n----------------------------")
        display_common_deployment_params(
            chain.id,
            deployer,
            os.environ["GOV_KEY"],
            os.environ["COMM_KEY"],
            os.environ["AGG_KEY"],
        )
        display_ethereum_deployment_params(
            os.environ["GOV_KEY"],
            os.environ["REDEMPTION_DELAY"],
            os.environ["GENESIS_STAKE"],
            os.environ["NUM_GENESIS_VALIDATORS"],
        )
        prompt_user_continue_or_break(
            "[WARNING] You are about to deploy to Ethereum Mainnet with the parameters above",
            False,
        )

    cf = deploy_Chainflip_contracts(
        deployer,
        KeyManager,
        Vault,
        StateChainGateway,
        FLIP,
        DeployerContract,
        AddressChecker,
        os.environ,
    )

    addressDump = {
        "KEY_MANAGER_ADDRESS": cf.keyManager.address,
        "SC_GATEWAY_ADDRESS": cf.stateChainGateway.address,
        "VAULT_ADDRESS": cf.vault.address,
        "FLIP_ADDRESS": cf.flip.address,
        "ADDRESS_CHECKER_ADDRESS": cf.addressChecker.address,
    }

    deploy_optional_contracts(cf, addressDump)

    print("Deployed with parameters\n----------------------------")
    display_common_deployment_params(
        chain.id, cf.deployer, cf.gov, cf.communityKey, cf.keyManager.getAggregateKey()
    )
    display_ethereum_deployment_params(
        cf.safekeeper, cf.redemptionDelay, cf.genesisStake, cf.numGenesisValidators
    )

    display_deployed_contracts(cf)

    store_artifacts(addressDump)


# As of now this is for Arbitrum
def deploy_secondary_evm():
    check_env_variables([])

    # For live deployment, add a confirmation step to allow the user to verify the parameters.
    if chain.id == arb_mainnet:
        # Print all the environment variables for mainnet deployment.
        print("\nTo be deployed with parameters\n----------------------------")
        display_common_deployment_params(
            chain.id,
            deployer,
            os.environ["GOV_KEY"],
            os.environ["COMM_KEY"],
            os.environ["AGG_KEY"],
        )
        prompt_user_continue_or_break(
            "[WARNING] You are about to deploy to Arbitrum Mainnet with the parameters above",
            False,
        )

    cf = deploy_contracts_secondary_evm(
        deployer,
        KeyManager,
        Vault,
        AddressChecker,
        os.environ,
    )

    addressDump = {
        "KEY_MANAGER_ADDRESS": cf.keyManager.address,
        "VAULT_ADDRESS": cf.vault.address,
        "ADDRESS_CHECKER_ADDRESS": cf.addressChecker.address,
    }

    deploy_optional_contracts(cf, addressDump)

    print("Deployed with parameters\n----------------------------")
    display_common_deployment_params(
        chain.id, deployer, cf.gov, cf.communityKey, cf.keyManager.getAggregateKey()
    )

    display_deployed_contracts(cf)

    store_artifacts(addressDump)


# Check that all environment variables are set when deploying to a live network.
def check_env_variables(env_var_names):
    common_env_var_names = [
        "AGG_KEY",
        "GOV_KEY",
        "COMM_KEY",
    ]
    for env_var_name in common_env_var_names + env_var_names:
        if env_var_name not in os.environ:
            raise Exception(f"Environment variable {env_var_name} is not set")


# Deploy extra contracts on local/devnets networks. Deploy USDC mock token to test
# swaps and liquidity provision, CFReceiverMock to test cross-chain messaging.
def deploy_optional_contracts(cf, addressDump):
    if chain.id in [arb_localnet, eth_localnet, hardhat]:
        cf.mockUSDC = deploy_usdc_contract(deployer, MockUSDC, cf_accs[0:10])
        addressDump["USDC_ADDRESS"] = cf.mockUSDC.address
    if chain.id not in [eth_mainnet, arb_mainnet]:
        cf.cfReceiverMock = deploy_new_cfReceiverMock(
            deployer, CFReceiverMock, cf.vault.address
        )
        addressDump["CF_RECEIVER_ADDRESS"] = cf.cfReceiverMock.address


def display_common_deployment_params(chain_id, deployer, govKey, commKey, aggKey):
    print(f"  Chain: {chain_id}")
    print(f"  Deployer: {deployer}")
    print(f"  Community Key: {commKey}")
    print(f"  Aggregate Key: {aggKey}")
    print(f"  GovKey: {govKey}")


def display_ethereum_deployment_params(
    safekeeper, redemption_delay, genesis_stake, num_genesis_validators
):
    print(f"  Safekeeper: {safekeeper}")
    print(f"  Redemption Delay: {redemption_delay}")
    print(f"  Genesis Stake: {genesis_stake}")
    print(f"  Genesis Stake / E_18: {int(genesis_stake)/E_18}")
    print(f"  Num Genesis Validators: {num_genesis_validators}")
    print(f"\nFLIP tokens will be minted to the Safekeeper account {safekeeper}")


def display_deployed_contracts(cf):
    print("\nDeployed contract addresses\n----------------------------")

    # Ethereum contracts
    if hasattr(cf, "deployerContract"):
        print(f"  DeployerContract: {cf.deployerContract.address}")
    if hasattr(cf, "stateChainGateway"):
        print(f"  StateChainGateway: {cf.stateChainGateway.address}")
    if hasattr(cf, "flip"):
        print(f"  FLIP: {cf.flip.address}")

    # Common contracts
    print(f"  KeyManager: {cf.keyManager.address}")
    print(f"  Vault: {cf.vault.address}")
    print(f"  AddressChecker: {cf.addressChecker.address}")

    # Contracts dependant on localnet/testnet/mainnet
    if hasattr(cf, "mockUSDC"):
        print(f"  USDC: {cf.mockUSDC.address}")
    if hasattr(cf, "cfReceiverMock"):
        print(f"  CfReceiver Mock: {cf.cfReceiverMock.address}")

    print("\n😎😎 Deployment success! 😎😎\n")


def store_artifacts(addressDump):
    if DEPLOY_ARTEFACT_ID:
        dir_path = os.path.dirname(os.path.abspath(__file__)) + "/.artefacts"

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        with open(f"{dir_path}/{DEPLOY_ARTEFACT_ID}.json", "w") as output_file:
            json.dump(addressDump, output_file, indent=2)
