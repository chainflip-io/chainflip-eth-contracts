from consts import *
from shared_tests import *
from brownie import reverts, web3, chain
from brownie.test import given, strategy

# FLIP, Vault and StakeManager inherit AccessValidator
def test_constructor(cf):
    accessValidators = [cf.flip, cf.stakeManager, cf.vault]
    for accessValidator in accessValidators:
        assert accessValidator.getKeyManager() == cf.keyManager

    whitelist = (strategy("address[]", unique=True),)


def test_updateKeyManager(cf, KeyManager):
    accessValidators = [cf.flip, cf.stakeManager, cf.vault]

    # Reusing current keyManager aggregateKey for simplicity
    newKeyManager = cf.DEPLOYER.deploy(
        KeyManager, cf.keyManager.getAggregateKey(), cf.gov
    )

    for accessValidator in accessValidators:
        updateKeyManager(accessValidator, cf.keyManager, newKeyManager)
        assert accessValidator.getKeyManager() == newKeyManager
