import sys
import os
import json

sys.path.append(os.path.abspath("tests"))
from consts import *
from brownie import chain, accounts, KeyManager, Vault, StakeManager, FLIP, MockUSDC
from deploy import deploy_set_Chainflip_contracts, deploy_usdc_contract


def main():
    AUTONOMY_SEED = os.environ["SEED"]
    DEPLOY_ARTEFACT_ID = os.environ.get("DEPLOY_ARTEFACT_ID")
    cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
    DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

    DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
    print(f"DEPLOYER = {DEPLOYER}")

    # Check that all environment variables are set when deploying to a live network
    # SEED and the endpoint are checked automatically by Brownie
    # env_var_names = ["AGG_KEY", "GOV_KEY", "COMM_KEY", "NUM_GENESIS_VALIDATORS", "GENESIS_STAKE"]
    env_var_names = ["GOV_KEY", "COMM_KEY", "NUM_GENESIS_VALIDATORS", "GENESIS_STAKE"]
    for env_var_name in env_var_names:
        if env_var_name not in os.environ:
            raise Exception(f"Environment variable {env_var_name} is not set")
        else:
            print(f"{env_var_name} = {os.environ[env_var_name]}")

    print(f"FLIP tokens will be minted to the GOV_KEY account {os.environ['GOV_KEY']}")

    # In case we manually call this script for live deployment, we add this a prompt for the user
    # to confirm all those values. If we do it via script then we can remove the printing above.
    # However, check with Tom that the prompt won't mess with his deployment scripts.
    if chain.id == 1:
        input(
            "\n[WARNING] You are about to deploy to the mainnet with the parameters above. Continue? [y/N]"
        )
        if input != "y":
            ## Gracefully exit the script with a message
            sys.exit("Deployment cancelled by user")

    cf = deploy_set_Chainflip_contracts(
        DEPLOYER, KeyManager, Vault, StakeManager, FLIP, os.environ
    )

    print(f"KeyManager: {cf.keyManager.address}")
    print(f"StakeManager: {cf.stakeManager.address}")
    print(f"FLIP: {cf.flip.address}")
    print(f"Vault: {cf.vault.address}")

    addressDump = {
        "KEY_MANAGER_ADDRESS": cf.keyManager.address,
        "STAKE_MANAGER_ADDRESS": cf.stakeManager.address,
        "VAULT_ADDRESS": cf.vault.address,
        "FLIP_ADDRESS": cf.flip.address,
    }

    # Deploy USDC mimic token only on private NATIVE network
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
