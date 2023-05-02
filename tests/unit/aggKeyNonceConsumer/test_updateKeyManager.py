from consts import *
from shared_tests import *
from brownie import reverts
from deploy import deploy_new_keyManager

# FLIP, Vault and StateChainGateway inherit AggKeyNonceConsumer
def test_constructor(cf):
    aggKeyNonceConsumers = [cf.stateChainGateway, cf.vault]
    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        assert aggKeyNonceConsumer.getKeyManager() == cf.keyManager


def test_updateKeyManager(cf, KeyManager):
    aggKeyNonceConsumers = [cf.stateChainGateway, cf.vault]

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


def test_updateKeyManager_rev_eoa(cf):
    aggKeyNonceConsumers = [cf.stateChainGateway, cf.vault]

    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        with reverts("Transaction reverted without a reason string"):
            signed_call_cf(cf, aggKeyNonceConsumer.updateKeyManager, cf.BOB)


def test_updateKeyManager_rev_wrongKeyManager(cf, mockKeyManagers):
    aggKeyNonceConsumers = [cf.stateChainGateway, cf.vault]

    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        with reverts("NonceCons: not consumeKeyNonce implementer"):
            signed_call_cf(cf, aggKeyNonceConsumer.updateKeyManager, mockKeyManagers[0])

        ## NOTE: Having a different return type won't cause a failure in AggKeyNonceConsumer
        ## We could enforce it manually if we use a low-level call but it's not problematic.
        with reverts("Transaction reverted without a reason string"):
            signed_call_cf(cf, aggKeyNonceConsumer.updateKeyManager, mockKeyManagers[1])

        with reverts("Transaction reverted without a reason string"):
            signed_call_cf(cf, aggKeyNonceConsumer.updateKeyManager, mockKeyManagers[2])

        with reverts("Transaction reverted without a reason string"):
            signed_call_cf(cf, aggKeyNonceConsumer.updateKeyManager, mockKeyManagers[3])

        # PROBLEMATIC-ish for both cases
        # with reverts("Transaction reverted without a reason string"):
        #     signed_call_cf(cf, aggKeyNonceConsumer.updateKeyManager, mockKeyManagers[4])

        # Should fail due to keyManager.getGovernanceKey()
        with reverts("Transaction reverted without a reason string"):
            signed_call_cf(cf, aggKeyNonceConsumer.updateKeyManager, mockKeyManagers[5])
        with reverts("Transaction reverted without a reason string"):
            signed_call_cf(cf, aggKeyNonceConsumer.updateKeyManager, mockKeyManagers[6])

    signed_call_cf(cf, cf.stateChainGateway.updateKeyManager, mockKeyManagers[7])
    # Vault checks getLastValidateTime
    with reverts("Transaction reverted without a reason string"):
        signed_call_cf(cf, cf.vault.updateKeyManager, mockKeyManagers[7])


def test_updateKeyManager_mock(cf, mockKeyManagers):
    signed_call_cf(cf, cf.stateChainGateway.updateKeyManager, mockKeyManagers[8])
    signed_call_cf(cf, cf.vault.updateKeyManager, mockKeyManagers[8])
