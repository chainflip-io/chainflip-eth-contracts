import sys
import os
import json

sys.path.append(os.path.abspath("tests"))
from consts import *
from brownie import chain, accounts, KeyManager, Vault, StakeManager, FLIP
from deploy import deploy_set_Chainflip_contracts


def main():
    AUTONOMY_SEED = os.environ["SEED"]
    DEPLOY_ARTEFACT_ID = os.environ.get("DEPLOY_ARTEFACT_ID")
    cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
    DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

    DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
    print(f"DEPLOYER = {DEPLOYER}")

    cf = deploy_set_Chainflip_contracts(
        DEPLOYER, DEPLOYER, KeyManager, Vault, StakeManager, FLIP, os.environ
    )

    print(f"KeyManager: {cf.keyManager.address}")
    print(f"StakeManager: {cf.stakeManager.address}")
    print(f"FLIP: {cf.flip.address}")
    print(f"Vault: {cf.vault.address}")

    if DEPLOY_ARTEFACT_ID:
        json_content = json.dumps(
            {
                "KEY_MANAGER_ADDRESS": cf.keyManager.address,
                "STAKE_MANAGER_ADDRESS": cf.stakeManager.address,
                "VAULT_ADDRESS": cf.vault.address,
                "FLIP_ADDRESS": cf.flip.address,
            }
        )

        dir_path = os.path.dirname(os.path.abspath(__file__)) + "/.artefacts/"

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        f = open(f"{dir_path}{DEPLOY_ARTEFACT_ID}.json", "w")
        f.write(json_content)
        f.close()
