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
    DeployerUpgradedContracts,
)
from deploy import deploy_upgraded_contracts

# This will deploy the new upgraded contracts (Vault and StakeManager). The FLIP
# contract and the KeyManager contract are not upgraded.


def main():
    AUTONOMY_SEED = os.environ["SEED"]
    DEPLOY_ARTEFACT_ID = os.environ.get("DEPLOY_ARTEFACT_ID")
    cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
    DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

    DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
    print(f"DEPLOYER = {DEPLOYER}")

    # Get necessary environment variables and throw if they are not set
    KEY_MANAGER_ADDRESS = os.environ["KEY_MANAGER_ADDRESS"]
    FLIP_ADDRESS = os.environ["FLIP_ADDRESS"]

    keyManager_address = f"0x{cleanHexStr(KEY_MANAGER_ADDRESS)}"
    flip_address = f"0x{cleanHexStr(FLIP_ADDRESS)}"

    cf = deploy_upgraded_contracts(
        DEPLOYER,
        KeyManager,
        Vault,
        StakeManager,
        FLIP,
        DeployerUpgradedContracts,
        keyManager_address,
        flip_address,
    )

    print("Deployed with parameters\n----------------------------")
    print(f"  ChainID: {chain.id}")
    print(f"  Deployer: {cf.deployer}")

    print("Legacy contracts still in use\n----------------------------")
    print(f"  KeyManager: {cf.keyManager.address}")
    print(f"  FLIP: {cf.flip.address}")

    print("Deployed contract addresses\n----------------------------")
    print(f"  DeployerContract: {cf.upgraderContract.address}")
    print(f"  StakeManager: {cf.stakeManager.address}")
    print(f"  Vault: {cf.vault.address}")

    print("\n😎😎 Deployment success! 😎😎")

    addressDump = {
        "KEY_MANAGER_ADDRESS": cf.keyManager.address,
        "STAKE_MANAGER_ADDRESS": cf.stakeManager.address,
        "VAULT_ADDRESS": cf.vault.address,
        "FLIP_ADDRESS": cf.flip.address,
    }

    if DEPLOY_ARTEFACT_ID:
        json_content = json.dumps(addressDump)

        dir_path = os.path.dirname(os.path.abspath(__file__)) + "/.artefacts/"

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        f = open(f"{dir_path}{DEPLOY_ARTEFACT_ID}.json", "w")
        f.write(json_content)
        f.close()
