from consts import *
from shared_tests import *
from brownie import reverts, web3, chain
from brownie.test import given, strategy

# FLIP, Vault and StakeManager inherit AggKeyNonceConsumer
def test_constructor(cf):
    aggKeyNonceConsumers = [cf.flip, cf.stakeManager, cf.vault]
    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        assert aggKeyNonceConsumer.getKeyManager() == cf.keyManager


def test_updateKeyManager(cf, KeyManager):
    aggKeyNonceConsumers = [cf.flip, cf.stakeManager, cf.vault]

    # Reusing current keyManager aggregateKey for simplicity
    newKeyManager = cf.DEPLOYER.deploy(
        KeyManager, cf.keyManager.getAggregateKey(), cf.gov
    )

    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        updateKeyManager(aggKeyNonceConsumer, cf.keyManager, newKeyManager)
        assert aggKeyNonceConsumer.getKeyManager() == newKeyManager
