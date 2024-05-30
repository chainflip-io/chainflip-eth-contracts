import sys
import os

sys.path.append(os.path.abspath("tests"))
from shared_tests import *
from utils import prompt_user_continue_or_break
from consts import *
from brownie import accounts, KeyManager, network

AUTONOMY_SEED = os.environ["SEED"]
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
print(f"DEPLOYER = {DEPLOYER}")


def main():
    print()


# This is to be used manually to insert the sc generated agg key for testnets
def insert_agg_key_from_sc():
    network.priority_fee("1 gwei")
    KEY_MANAGER_ADDRESS = os.environ["KEY_MANAGER_ADDRESS"]
    keyManager = KeyManager.at(KEY_MANAGER_ADDRESS)

    # Assumption that this is a long hex string without 0x
    x = os.environ["X_AGG_KEY"]
    parity = os.environ["PARITY"]

    # parity should be a "Odd" or "Even" otherwise it will fail
    assert parity in ["Even", "Odd"], "Parity should be Even or Odd"
    parity = "00" if parity == "Even" else "01"
    newAggKey = [int(x, 16), int(parity, 16)]

    print(f"Setting the aggregate key to {newAggKey}")
    prompt_user_continue_or_break("", False)

    tx = keyManager.setAggKeyWithGovKey(
        newAggKey, {"from": DEPLOYER, "required_confs": 1}
    )

    tx.info()
    print(f"Succesfullly updated the aggregate key to {newAggKey}")
