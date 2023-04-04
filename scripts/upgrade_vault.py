import sys
import os

sys.path.append(os.path.abspath("tests"))
from consts import *
from brownie import chain, accounts, KeyManager, Vault, StakeManager, FLIP, network

AUTONOMY_SEED = os.environ["SEED"]
DEPLOY_ARTEFACT_ID = os.environ.get("DEPLOY_ARTEFACT_ID")
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
print(f"DEPLOYER = {DEPLOYER}")

network.priority_fee("1 gwei")


def main():
    print()


def upgrade_empty_vault():
    FLIP_ADDRESS = os.environ["FLIP_ADDRESS"]
    STAKE_MANAGER_ADDRESS = os.environ["STAKE_MANAGER_ADDRESS"]
    VAULT_ADDRESS = os.environ["VAULT_ADDRESS"]
    KEY_MANAGER_ADDRESS = os.environ["KEY_MANAGER_ADDRESS"]

    # Ensure all the addresses are contracts
    keyManager = KeyManager.at(KEY_MANAGER_ADDRESS)
    vault = Vault.at(VAULT_ADDRESS)
    stakeManager = StakeManager.at(STAKE_MANAGER_ADDRESS)
    flip = FLIP.at(FLIP_ADDRESS)

    new_vault = deploy_vault(keyManager)
    whitelist_new_vault(keyManager, vault, stakeManager, flip, new_vault)


def deploy_vault(keyManager):
    vault = Vault.deploy(keyManager, {"from": DEPLOYER, "required_confs": 1})
    print(f"Vault deployed at {vault.address}")
    return vault.address


def whitelist_new_vault(keyManager, vault, stakeManager, flip, new_vault):

    # Ensure that the initial addresses are whitelisted
    whitelisted = [vault, stakeManager, flip]
    assert keyManager.getNumberWhitelistedAddresses() == len(whitelisted) == 3
    for address in [vault, stakeManager, flip]:
        assert keyManager.canConsumeKeyNonce(address)

    # Whitelist the new Vault instead of the old Vault (no need to move funds as the Vault is empty)
    # This should pass as there is the default AggKey
    toWhitelist = [new_vault, stakeManager, flip]

    # We need to sync the nonce if this is not the first transaction
    syncNonce(keyManager)

    args = [whitelisted, toWhitelist]

    callDataNoSig = keyManager.updateCanConsumeKeyNonce.encode_input(
        agg_null_sig(keyManager, chain.id), *args
    )
    tx = keyManager.updateCanConsumeKeyNonce(
        AGG_SIGNER_1.getSigData(callDataNoSig, keyManager),
        *args,
        {"from": DEPLOYER, "required_confs": 1},
    )

    assert keyManager.getNumberWhitelistedAddresses() == len(toWhitelist) == 3
    for address in [new_vault, stakeManager, flip]:
        assert keyManager.canConsumeKeyNonce(address)
    assert keyManager.canConsumeKeyNonce(vault) == False

    tx.info()
    print("Succesfully updated the whitelist")


# NOTE: This might be called first to set the AggKey to a known key. That is in the case
# we have deployed the initial contracts with a dummy AggKey. Then it can be called two
# days after upgrading the Vault to set back the dummy AggKey. This is a mock of what
# should be done via multisig, as the governance in the real contracts will be the multisig.
def update_agg_key():
    KEY_MANAGER_ADDRESS = os.environ["KEY_MANAGER_ADDRESS"]
    keyManager = KeyManager.at(KEY_MANAGER_ADDRESS)

    newAggKey = os.environ["NEW_AGG_KEY"]

    newAggKey = getKeysFromAggKey(newAggKey)

    # NOTE: This will fail if two days haven't passed since deployment or since
    # last time a signature was verified.
    tx = keyManager.setAggKeyWithGovKey(
        newAggKey, {"from": DEPLOYER, "required_confs": 1}
    )

    tx.info()
    assert keyManager.getAggregateKey() == newAggKey
    print(f"Succesfullly updated the aggregate key to {newAggKey}")
