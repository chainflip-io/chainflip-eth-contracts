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
        tx = signed_call_cf(
            cf, aggKeyNonceConsumer.updateKeyManager, newKeyManager, False
        )
        assert aggKeyNonceConsumer.getKeyManager() == newKeyManager
        assert tx.events["UpdatedKeyManager"][0].values()[0] == newKeyManager


def test_updateKeyManager_rev_eoa(cf):
    aggKeyNonceConsumers = [cf.stateChainGateway, cf.vault]

    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        with reverts("Transaction reverted without a reason string"):
            signed_call_cf(cf, aggKeyNonceConsumer.updateKeyManager, cf.BOB, False)


def test_updateKeyManager_notOmit(cf, mockKeyManagers, KeyManager):
    aggKeyNonceConsumers = [cf.stateChainGateway, cf.vault]

    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        for kmMocks in mockKeyManagers:
            for kmMock in kmMocks:
                with reverts("Transaction reverted without a reason string"):
                    signed_call_cf(
                        cf, aggKeyNonceConsumer.updateKeyManager, kmMock, False
                    )

    newKeyManager = deploy_new_keyManager(
        cf.SAFEKEEPER,
        KeyManager,
        AGG_SIGNER_2.getPubData(),
        cf.gov,
        cf.COMMUNITY_KEY,
    )

    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        with reverts("Transaction reverted without a reason string"):
            signed_call_cf(
                cf, aggKeyNonceConsumer.updateKeyManager, newKeyManager, False
            )

    newKeyManager = deploy_new_keyManager(
        cf.SAFEKEEPER,
        KeyManager,
        cf.keyManager.getAggregateKey(),
        cf.gov,
        cf.COMMUNITY_KEY,
    )

    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        signed_call_cf(cf, aggKeyNonceConsumer.updateKeyManager, newKeyManager, False)

    assert newKeyManager.getGovernanceKey() == cf.gov
    assert newKeyManager.getCommunityKey() == cf.COMMUNITY_KEY

    _emergency_withdrawals(cf, cf.gov, cf.COMMUNITY_KEY)


def test_updateKeyManager_arbitrary_rev_omit(cf, mockKeyManagers, KeyManagerMock5):
    aggKeyNonceConsumers = [cf.stateChainGateway, cf.vault]

    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        for kmMocks in mockKeyManagers:
            for kmMock in kmMocks[:4]:
                with reverts("Transaction reverted without a reason string"):
                    signed_call_cf(
                        cf, aggKeyNonceConsumer.updateKeyManager, kmMock, True
                    )
            # Vault checks getLastValidateTime
            with reverts("Transaction reverted without a reason string"):
                signed_call_cf(cf, cf.vault.updateKeyManager, kmMocks[4], True)

    # Check that even omitting it will revert if the addresses are zero
    km_zero_govKey = cf.SAFEKEEPER.deploy(
        KeyManagerMock5,
        ZERO_ADDR,
        cf.keyManager.getCommunityKey(),
    )
    km_zero_commKey = cf.SAFEKEEPER.deploy(
        KeyManagerMock5,
        cf.keyManager.getGovernanceKey(),
        ZERO_ADDR,
    )
    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        with reverts("Transaction reverted without a reason string"):
            signed_call_cf(
                cf, aggKeyNonceConsumer.updateKeyManager, km_zero_govKey, True
            )
        with reverts("Transaction reverted without a reason string"):
            signed_call_cf(
                cf, aggKeyNonceConsumer.updateKeyManager, km_zero_commKey, True
            )

    _emergency_withdrawals(cf, cf.gov, cf.COMMUNITY_KEY)


# Separating success tests because once a keyManagerMock is set the following ones will fail
def test_updateKeyManager_arbitrary_omit_4(cf, mockKeyManagers):
    signed_call_cf(
        cf, cf.stateChainGateway.updateKeyManager, mockKeyManagers[0][4], True
    )
    _emergency_withdrawal_gateway(cf, cf.BOB, cf.DENICE)
    _emergency_withdrawal_vault(cf, cf.gov, cf.COMMUNITY_KEY)


def test_updateKeyManager_valid_omit_4(cf, mockKeyManagers):
    signed_call_cf(
        cf, cf.stateChainGateway.updateKeyManager, mockKeyManagers[1][4], True
    )
    _emergency_withdrawals(cf, cf.gov, cf.COMMUNITY_KEY)


def test_updateKeyManager_arbitrary_omit_5(cf, mockKeyManagers):
    aggKeyNonceConsumers = [cf.stateChainGateway, cf.vault]

    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        signed_call_cf(
            cf, aggKeyNonceConsumer.updateKeyManager, mockKeyManagers[0][5], True
        )

    _emergency_withdrawals(cf, cf.BOB, cf.DENICE)


def test_updateKeyManager_valid_omit_5(cf, mockKeyManagers):
    aggKeyNonceConsumers = [cf.stateChainGateway, cf.vault]

    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        signed_call_cf(
            cf, aggKeyNonceConsumer.updateKeyManager, mockKeyManagers[1][5], True
        )

    _emergency_withdrawals(cf, cf.gov, cf.COMMUNITY_KEY)


# Test that in any succesfull updateKeyManager an emergency withdrawal can be performed in some way
def _emergency_withdrawal_vault(cf, govKey, communityKey):
    # Fund contract
    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT * 10)
    cf.flip.transfer(cf.vault, TEST_AMNT * 20, {"from": govKey})

    assert cf.vault.balance() > 0
    assert cf.flip.balanceOf(cf.vault) > 0
    iniBals_flip_gov = cf.flip.balanceOf(govKey)
    iniBals_native_gov = govKey.balance()

    # Proceed with emergency withdrawal
    cf.vault.suspend({"from": govKey})
    cf.vault.disableCommunityGuard({"from": communityKey})

    chain.sleep(AGG_KEY_EMERGENCY_TIMEOUT * 10)
    tokenList = [NATIVE_ADDR, cf.flip]
    cf.vault.govWithdraw(tokenList, {"from": govKey})
    assert cf.vault.balance() == 0
    assert cf.flip.balanceOf(cf.vault) == 0
    assert cf.flip.balanceOf(govKey) == iniBals_flip_gov + TEST_AMNT * 20
    # Some gas is spent in the process
    assert govKey.balance() > iniBals_native_gov


def _emergency_withdrawal_gateway(cf, govKey, communityKey):
    amount_to_recover = cf.flip.balanceOf(cf.stateChainGateway)

    assert cf.flip.balanceOf(cf.stateChainGateway) > 0
    iniBals_gov = cf.flip.balanceOf(govKey)

    # Proceed with emergency withdrawal
    cf.stateChainGateway.suspend({"from": govKey})
    cf.stateChainGateway.disableCommunityGuard({"from": communityKey})
    cf.stateChainGateway.govWithdraw({"from": govKey})
    assert cf.flip.balanceOf(cf.stateChainGateway) == 0
    assert cf.flip.balanceOf(govKey) == iniBals_gov + amount_to_recover

    assert cf.flip.getIssuer() == govKey

    # Ensure that we can also update the flip issuer althouth its already the govKey
    with reverts(REV_MSG_FLIP_ISSUER):
        cf.stateChainGateway.govUpdateFlipIssuer({"from": govKey})


def _emergency_withdrawals(cf, govKey, communityKey):
    _emergency_withdrawal_vault(cf, govKey, communityKey)
    _emergency_withdrawal_gateway(cf, govKey, communityKey)
