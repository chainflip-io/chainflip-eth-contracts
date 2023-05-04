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
        for mockKeyManager in mockKeyManagers[:7]:
            with reverts("Transaction reverted without a reason string"):
                signed_call_cf(cf, aggKeyNonceConsumer.updateKeyManager, mockKeyManager)


# Separating this from the previous one because once one passes the rest will fail
def test_updateKeyManager_0(cf, mockKeyManagers):
    signed_call_cf(cf, cf.stateChainGateway.updateKeyManager, mockKeyManagers[8])
    # Vault checks getLastValidateTime
    with reverts("Transaction reverted without a reason string"):
        signed_call_cf(cf, cf.vault.updateKeyManager, mockKeyManagers[8])


def test_updateKeyManager_1(cf, mockKeyManagers):
    signed_call_cf(cf, cf.stateChainGateway.updateKeyManager, mockKeyManagers[9])
    signed_call_cf(cf, cf.vault.updateKeyManager, mockKeyManagers[9])


def test_updateKeyManager_error_notCatastrophic(cf, mockKeyManagers):
    # Insert a keyManager that has all the functions except consumeKeyNonce
    signed_call_cf(cf, cf.stateChainGateway.updateKeyManager, mockKeyManagers[10])
    signed_call_cf(cf, cf.vault.updateKeyManager, mockKeyManagers[10])

    # Fund both the Vault and the StateChainGateway with some funds
    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT * 10)
    cf.flip.transfer(cf.vault, TEST_AMNT * 20, {"from": cf.SAFEKEEPER})
    cf.flip.transfer(cf.stateChainGateway, TEST_AMNT * 30, {"from": cf.SAFEKEEPER})

    with reverts("Transaction reverted without a reason string"):
        transfer_native(cf, cf.vault, cf.ALICE, TEST_AMNT)

    with reverts("Transaction reverted without a reason string"):
        registerRedemptionTest(
            cf,
            cf.stateChainGateway,
            JUNK_HEX,
            MIN_FUNDING,
            MIN_FUNDING,
            cf.DENICE,
            getChainTime() + REDEMPTION_DELAY + 5,
        )

    # Proceed with emergency withdrawals
    assert cf.vault.balance() > 0
    assert cf.flip.balanceOf(cf.vault) > 0
    assert cf.flip.balanceOf(cf.stateChainGateway) > 0

    # TODO: It was failing because we have not enforced the new KeyManager
    # to have the same aggregateKey, govKey and AggKey as the previous one.
    # Should we enforce that??

    cf.stateChainGateway.suspend({"from": cf.GOVERNOR})
    cf.stateChainGateway.disableCommunityGuard({"from": cf.COMMUNITY_KEY})
    cf.stateChainGateway.govWithdraw({"from": cf.GOVERNOR})
    assert cf.flip.balanceOf(cf.stateChainGateway) == 0

    cf.vault.suspend({"from": cf.GOVERNOR})
    cf.vault.disableCommunityGuard({"from": cf.COMMUNITY_KEY})

    chain.sleep(AGG_KEY_EMERGENCY_TIMEOUT + 1)
    tokenList = [NATIVE_ADDR, cf.flip]
    cf.vault.govWithdraw(tokenList, {"from": cf.GOVERNOR})
    assert cf.vault.balance() == 0
    assert cf.flip.balanceOf(cf.vault) == 0
