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
    StateChainGateway,
    FLIP,
    DeployerStateChainGateway,
)
from deploy import deploy_new_vault, deploy_new_stateChainGateway


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

# This script, so far, supports deploying a new StateChainGateway and/or a new Vault.
# Run deploy_vault_gateway to deploy both
# Run deploy_vault to deploy only the new Vault
# Run deploy_stateChainGateway to deploy only the new StateChainGateway


def main():
    print()


def deploy_vault_gateway():
    _deploy_vault()
    _deploy_stateChainGateway()
    store_artifacts()


# This will deploy the new Vault. It assumes KeyManager is already deployed.
# The StateChainGateway and KeyManager contracts remains unchanged.
def deploy_vault():
    _deploy_vault()
    store_artifacts()


# This will deploy the new StateChainGateway. It assumes a StateChainGateway and a KeyManager
# are already deployed. The Vault contract remains unchanged.
def deploy_stateChainGateway():
    _deploy_stateChainGateway()
    store_artifacts()


def _deploy_vault():
    new_vault = deploy_new_vault(DEPLOYER, Vault, KeyManager, keyManager_address)
    addressDump["VAULT_ADDRESS"] = new_vault.address


def _deploy_stateChainGateway():
    FLIP_ADDRESS = os.environ["FLIP_ADDRESS"]
    flip_address = f"0x{cleanHexStr(FLIP_ADDRESS)}"

    (deployerStateChainGateway, new_stateChainGateway) = deploy_new_stateChainGateway(
        DEPLOYER,
        KeyManager,
        StateChainGateway,
        FLIP,
        DeployerStateChainGateway,
        keyManager_address,
        flip_address,
        MIN_FUNDING,
    )
    addressDump["SC_GATEWAY_ADDRESS"] = new_stateChainGateway.address
    addressDump["DEPLOYER_SM"] = deployerStateChainGateway.address
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
    if "SC_GATEWAY_ADDRESS" in addressDump:
        print(f"  DeployerContract: {addressDump['DEPLOYER_SM']}")
        print(f"  StateChainGateway: {addressDump['SC_GATEWAY_ADDRESS']}")
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
