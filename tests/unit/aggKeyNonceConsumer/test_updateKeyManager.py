from consts import *
from shared_tests import *
from deploy import deploy_new_keyManager

# FLIP, Vault and StakeManager inherit AggKeyNonceConsumer
def test_constructor(cf):
    aggKeyNonceConsumers = [cf.flip, cf.stakeManager, cf.vault]
    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        assert aggKeyNonceConsumer.getKeyManager() == cf.keyManager


def test_updateKeyManager(cf, KeyManager):
    aggKeyNonceConsumers = [cf.flip, cf.stakeManager, cf.vault]

    # Reusing current keyManager aggregateKey for simplicity
    newKeyManager = deploy_new_keyManager(
        cf.SAFEKEEPER,
        KeyManager,
        cf.keyManager.getAggregateKey(),
        cf.gov,
        cf.COMMUNITY_KEY,
    )

    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        tx = signed_call_cf(cf, aggKeyNonceConsumer.updateKeyManager, newKeyManager)
        assert aggKeyNonceConsumer.getKeyManager() == newKeyManager
        assert tx.events["UpdatedKeyManager"][0].values()[0] == newKeyManager
