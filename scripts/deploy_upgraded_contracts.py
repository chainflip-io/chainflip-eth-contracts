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
    DeployerStakeManager,
)
from deploy import deploy_new_vault, deploy_new_stakeManager


AUTONOMY_SEED = os.environ["SEED"]
DEPLOY_ARTEFACT_ID = os.environ.get("DEPLOY_ARTEFACT_ID")
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
print(f"DEPLOYER = {DEPLOYER}")

# Get necessary environment variables and throw if they are not set
KEY_MANAGER_ADDRESS = os.environ["KEY_MANAGER_ADDRESS"]

keyManager_address = f"0x{cleanHexStr(KEY_MANAGER_ADDRESS)}"
keyManager = KeyManager.at(KEY_MANAGER_ADDRESS)

addressDump = {}


def main():
    print()


def deploy_vault_stakemanager():
    _deploy_vault()
    _deploy_stakeManager()
    store_artifacts()


# This will deploy the new Vault. It assumes KeyManager is already deployed.
# The StakeManager and KeyManager contracts remains unchanged.
def deploy_vault():
    _deploy_vault()
    store_artifacts()


def _deploy_vault():
    new_vault = deploy_new_vault(DEPLOYER, Vault, KeyManager, keyManager_address)
    addressDump["VAULT_ADDRESS"] = new_vault.address


# This will deploy the new StakeManager. It assumes a StakeManager and a KeyManager
# are already deployed. The Vault contract remains unchanged.
def deploy_stakeManager():
    _deploy_stakeManager()
    store_artifacts()


def _deploy_stakeManager():
    FLIP_ADDRESS = os.environ["FLIP_ADDRESS"]
    flip_address = f"0x{cleanHexStr(FLIP_ADDRESS)}"

    (deployerStakeManager, new_stakeManager) = deploy_new_stakeManager(
        DEPLOYER,
        KeyManager,
        StakeManager,
        FLIP,
        DeployerStakeManager,
        keyManager_address,
        flip_address,
    )
    addressDump["STAKE_MANAGER_ADDRESS"] = new_stakeManager.address
    addressDump["DEPLOYER_SM"] = deployerStakeManager.address
    addressDump["FLIP_ADDRESS"] = flip_address


def store_artifacts():
    print("Deployed with parameters\n----------------------------")
    print(f"  ChainID: {chain.id}")
    print(f"  Deployer: {DEPLOYER}")

    print("Legacy contracts still in use\n----------------------------")
    print(f"  KeyManager: {keyManager_address}")
    if "FLIP_ADDRESS" in addressDump:
        print(f"  FLIP: {addressDump['FLIP_ADDRESS']}")

    print("New deployed contract addresses\n----------------------------")
    if "STAKE_MANAGER_ADDRESS" in addressDump:
        print(f"  DeployerContract: {addressDump['DEPLOYER_SM']}")
        print(f"  StakeManager: {addressDump['STAKE_MANAGER_ADDRESS']}")
    if "VAULT_ADDRESS" in addressDump:
        print(f"  Vault: {addressDump['VAULT_ADDRESS']}")

    print("\n😎😎 Deployment success! 😎😎")

    if DEPLOY_ARTEFACT_ID:
        json_content = json.dumps(addressDump)

        dir_path = os.path.dirname(os.path.abspath(__file__)) + "/.artefacts/"

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        f = open(f"{dir_path}{DEPLOY_ARTEFACT_ID}.json", "w")
        f.write(json_content)
        f.close()
