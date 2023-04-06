import sys
import os
import json

sys.path.append(os.path.abspath("tests"))
from consts import *
from brownie import (
    chain,
    accounts,
    KeyManager,
    Vault,
    StakeManager,
    FLIP,
    MockUSDC,
    DeployerContract,
)
from deploy import deploy_Chainflip_contracts, deploy_usdc_contract


def main():
    AUTONOMY_SEED = os.environ["SEED"]
    DEPLOY_ARTEFACT_ID = os.environ.get("DEPLOY_ARTEFACT_ID")
    cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
    DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

    DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
    print(f"DEPLOYER = {DEPLOYER}")

    # Check that all environment variables are set when deploying to a live network.
    # SEED and the endpoint are checked automatically by Brownie.
    # env_var_names = [
    #     "AGG_KEY",
    #     "GOV_KEY",
    #     "COMM_KEY",
    #     "GENESIS_STAKE",
    #     "NUM_GENESIS_VALIDATORS",
    # ]
    # for env_var_name in env_var_names:
    #     if env_var_name not in os.environ:
    #         raise Exception(f"Environment variable {env_var_name} is not set")

    # For live deployment, add a confirmation step to allow the user to verify the parameters.
    if chain.id == 1:
        # Print all the environment variables for mainnet deployment.
        print("\nTo be deployed with parameters\n----------------------------")
        print(f"  ChainID: {chain.id} - ETHEREUM MAINNET")
        print(f"  Deployer: {DEPLOYER}")
        print(f"  Safekeeper & GovKey: {os.environ['GOV_KEY']}")
        print(f"  Community Key: {os.environ['COMM_KEY']}")
        print(f"  Aggregate Key: {os.environ['AGG_KEY']}")
        print(f"  Genesis Stake: {os.environ['GENESIS_STAKE']}")
        print(f"  Num Genesis Validators: {os.environ['NUM_GENESIS_VALIDATORS']}")
        print(
            f"\nFLIP tokens will be minted to the Safekeeper account {os.environ['GOV_KEY']}"
        )
        user_input = input(
            "\n[WARNING] You are about to deploy to the mainnet with the parameters above. Continue? [y/N] "
        )
        if user_input != "y":
            ## Gracefully exit the script with a message.
            sys.exit("Deployment cancelled by user")

    cf = deploy_Chainflip_contracts(
        DEPLOYER, KeyManager, Vault, StakeManager, FLIP, DeployerContract, os.environ
    )

    print("Deployed with parameters\n----------------------------")
    print(f"  ChainID: {chain.id}")
    print(f"  Deployer: {cf.deployer}")
    print(f"  Safekeeper: {cf.safekeeper}")
    print(f"  GovKey: {cf.gov}")
    print(f"  Community Key: {cf.communityKey}")
    print(f"  Aggregate Key: {cf.keyManager.getAggregateKey()}")
    print(f"  Genesis Stake: {cf.genesisStake}")
    print(f"  Num Genesis Validators: {cf.numGenesisValidators}" + "\n")

    print("Deployed contract addresses\n----------------------------")
    print(f"  DeployerContract: {cf.deployerContract.address}")
    print(f"  KeyManager: {cf.keyManager.address}")
    print(f"  StakeManager: {cf.stakeManager.address}")
    print(f"  FLIP: {cf.flip.address}")
    print(f"  Vault: {cf.vault.address}")

    print("\n😎😎 Deployment success! 😎😎")

    addressDump = {
        "KEY_MANAGER_ADDRESS": cf.keyManager.address,
        "STAKE_MANAGER_ADDRESS": cf.stakeManager.address,
        "VAULT_ADDRESS": cf.vault.address,
        "FLIP_ADDRESS": cf.flip.address,
    }

    # Deploy USDC mimic token only on private EVM network
    if chain.id == 10997:
        cf.mockUSDC = deploy_usdc_contract(DEPLOYER, MockUSDC, cf_accs[0:10])
        print(f"USDC: {cf.mockUSDC.address}")
        addressDump["USDC_ADDRESS"] = cf.mockUSDC.address

    if DEPLOY_ARTEFACT_ID:
        json_content = json.dumps(addressDump)

        dir_path = os.path.dirname(os.path.abspath(__file__)) + "/.artefacts/"

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        f = open(f"{dir_path}{DEPLOY_ARTEFACT_ID}.json", "w")
        f.write(json_content)
        f.close()
