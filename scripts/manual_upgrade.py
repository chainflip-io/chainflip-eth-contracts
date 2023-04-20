import sys
import os

sys.path.append(os.path.abspath("tests"))
from shared_tests import *
from consts import *
from brownie import (
    chain,
    accounts,
    KeyManager,
    Vault,
    StakeManager,
    FLIP,
    network,
    web3,
)

AUTONOMY_SEED = os.environ["SEED"]
DEPLOY_ARTEFACT_ID = os.environ.get("DEPLOY_ARTEFACT_ID")
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
print(f"DEPLOYER = {DEPLOYER}")

network.priority_fee("1 gwei")


def main():
    print()


# NOTE: This is to be used to manually upgrade contracts when having control over
# the governance key and no CF network has been deployed yet. To be used in mainnet
# if there is a need to upgrade a contract before the Vault has any funds. The
# StakeManager would require moving the genesis Stake between Vaults.

# Steps:

# 1. Deploy the new contracts using deploy_upgraded_contracts.py. Either deploy
#    a new vault (deploy_vault) or a new stakeManager (deploy_stakeManager) or both
#    (deploy_vault_stakemanager).

# 2. Assuming no CF network has been deployed yet and that the current AggKey is a
#    dummy one, we can wait _AGG_KEY_TIMEOUT (2 days) to set a known AggKey. This
#    will be a single schnorr key that is known. This should be done as shown in
#    update_agg_key. However, this should be done via multisig so this is just a
#    mockup of what should be done.

# 3. Input the known private key in consts.py as AGG_PRIV_HEX_1.

# 4. If we are upgrading a StakeManager contract, we need to register a claim to
#    move all the FLIP to the new StakeManager. An EMPTY vault doesn't require
#    any extra step but a Vault with funds require a transfer of tokens to the
#    new vault. For this initial upgrade, this should not be needed.

# 5. If we have registered a claim, wait for CLAIM_DELAY and execute it via
#    execute_claim. This will move all the FLIP to the new StakeManager.


# NOTE: This will fail if two days haven't passed since deployment or since
# last time a signature was verified. It will also fail if the DEPLOYER is not
# the governance key. If the govKey is a multisig it this will fail.
def update_agg_key():
    KEY_MANAGER_ADDRESS = os.environ["KEY_MANAGER_ADDRESS"]
    keyManager = KeyManager.at(KEY_MANAGER_ADDRESS)

    newAggKey = os.environ["NEW_AGG_KEY"]

    newAggKey = getKeysFromAggKey(newAggKey)

    tx = keyManager.setAggKeyWithGovKey(
        newAggKey, {"from": DEPLOYER, "required_confs": 1}
    )

    tx.info()
    assert keyManager.getAggregateKey() == newAggKey
    print(f"Succesfullly updated the aggregate key to {newAggKey}")


# Assumption that we have the private key of the aggregate key
def register_claim_genesis_flip():
    STAKE_MANAGER_ADDRESS = os.environ["STAKE_MANAGER_ADDRESS"]
    NEW_STAKE_MANAGER_ADDRESS = os.environ["NEW_STAKE_MANAGER_ADDRESS"]
    FLIP_ADDRESS = os.environ["FLIP_ADDRESS"]
    KEY_MANAGER_ADDRESS = os.environ["KEY_MANAGER_ADDRESS"]

    assert NEW_STAKE_MANAGER_ADDRESS != STAKE_MANAGER_ADDRESS, "Same address"

    flip = FLIP.at(FLIP_ADDRESS)
    stakeManager = StakeManager.at(STAKE_MANAGER_ADDRESS)
    keyManager = KeyManager.at(KEY_MANAGER_ADDRESS)

    flip_balance = flip.balanceOf(stakeManager.address)

    assert flip_balance > 0, "StakeManager has no FLIP"

    print(
        f"FLIP balance of StakeManager {flip_balance}. Registering a claim to the new StakeManager {NEW_STAKE_MANAGER_ADDRESS}"
    )
    user_input = input("Continue? (y/[N])")
    if user_input not in ["y", "Y", "yes", "Yes", "YES"]:
        sys.exit("Canceled by the user")

    syncNonce(keyManager)

    # Setting an infinit expiry time
    args = [JUNK_HEX, flip_balance, NEW_STAKE_MANAGER_ADDRESS, 2**47]

    tx = signed_call(
        keyManager, stakeManager.registerClaim, AGG_SIGNER_1, DEPLOYER, *args
    )

    tx.info()


def execute_claim():
    STAKE_MANAGER_ADDRESS = os.environ["STAKE_MANAGER_ADDRESS"]

    # For testing purposes we want to speed up time
    # chain.sleep(CLAIM_DELAY)

    # This can fail if the claim is not registered or if the CLAIM_DELAY time has not passed
    tx = StakeManager.at(STAKE_MANAGER_ADDRESS).executeClaim(
        JUNK_HEX, {"from": DEPLOYER, "required_confs": 1}
    )
    tx.info()
