from consts import *
from shared_tests import *
from brownie import reverts, web3, chain
from brownie.test import given, strategy
from deploy import deploy_new_stateChainGateway, deploy_new_vault, deploy_new_keyManager

# Goal is to test upgrading contracts (deploy a new version) except FLIP.


## Update processs KeyManager:
# Deploy new keyManager
# Update all keyManager references
# Start signing with the new keyManager's address
def test_upgrade_keyManager(cf, KeyManager):
    args = [[NATIVE_ADDR, cf.ALICE, TEST_AMNT]]

    # Try initial transfer to later test a replay attack on the newly deployed keyManager
    contractMsgHash = Signer.generate_contractMsgHash(cf.vault.transfer, *args)
    msgHash = Signer.generate_msgHash(
        contractMsgHash, nonces, cf.keyManager.address, cf.vault.address
    )
    sigData = AGG_SIGNER_1.generate_sigData(msgHash, nonces)

    cf.vault.transfer(sigData, *args, {"from": cf.ALICE})

    # Reusing current keyManager aggregateKey for simplicity
    newKeyManager = deploy_new_keyManager(
        cf.DENICE, KeyManager, cf.keyManager.getAggregateKey(), cf.gov, cf.COMMUNITY_KEY
    )

    aggKeyNonceConsumers = [cf.vault, cf.stateChainGateway]
    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        signed_call_cf(cf, aggKeyNonceConsumer.updateKeyManager, newKeyManager, False)
        assert aggKeyNonceConsumer.getKeyManager() == newKeyManager

    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        # Check that messages signed with old keyManager's address revert in the new one
        with reverts(REV_MSG_SIG):
            signed_call_cf(
                cf, aggKeyNonceConsumer.updateKeyManager, NON_ZERO_ADDR, False
            )

        # Try one validation per contract to check that they can validate
        signed_call_cf(
            cf,
            aggKeyNonceConsumer.updateKeyManager,
            aggKeyNonceConsumer.getKeyManager(),
            False,
            keyManager=newKeyManager,
        )

    # Try replay attack using transaction called on the previous keyManager
    # nonce is available on the new keyManager so it relies on signing over the keyManager address
    with reverts(REV_MSG_SIG):
        cf.vault.transfer(
            sigData, [NATIVE_ADDR, cf.ALICE, TEST_AMNT], {"from": cf.ALICE}
        )

    # Check that a new transfer works and uses the new keyManager
    currentNonce = nonces[AGG]
    assert newKeyManager.isNonceUsedByAggKey(currentNonce) == False

    args = [[NATIVE_ADDR, cf.ALICE, TEST_AMNT]]
    contractMsgHash = Signer.generate_contractMsgHash(cf.vault.transfer, *args)
    msgHash = Signer.generate_msgHash(
        contractMsgHash, nonces, newKeyManager.address, cf.vault.address
    )
    sigData = AGG_SIGNER_1.generate_sigData(msgHash, nonces)

    cf.vault.transfer(sigData, [NATIVE_ADDR, cf.ALICE, TEST_AMNT], {"from": cf.ALICE})

    assert newKeyManager.isNonceUsedByAggKey(currentNonce) == True

    # Try another replay attack
    with reverts(REV_MSG_KEYMANAGER_NONCE):
        cf.vault.transfer(
            sigData, [NATIVE_ADDR, cf.ALICE, TEST_AMNT], {"from": cf.ALICE}
        )


## Update process Vault:
# Deploy new Vault. New Vault can start generating deposit addresses.
# Old vault still needs to be active to be able to fetch active swaps.
# Transfer tokens from old Vault to new Vault.
# At the end we will anyway have to do a final transfer from Vault to Vault, so no need to transfer all the balance now.
# Once a certain amount of time has passed (no more old vault fetches) we transfer remaining amount to new Vault
@given(
    st_sender=strategy("address"),
)
def test_upgrade_Vault(cf, Vault, Deposit, st_sender, KeyManager, token):

    totalFunds = cf.DENICE.balance() / 10
    # Replicate a vault with funds - 1000 NATIVE
    cf.DENICE.transfer(cf.vault, totalFunds)

    newVault = deploy_new_vault(cf.DENICE, Vault, KeyManager, cf.keyManager)

    args = [[NATIVE_ADDR, cf.ALICE, TEST_AMNT]]

    # Vault can now validate and fetch but it has zero balance so it can't transfer
    tx = signed_call_cf(cf, newVault.transfer, *args, sender=st_sender)

    assert tx.events["TransferNativeFailed"][0].values() == [
        cf.ALICE,
        TEST_AMNT,
    ]

    # with a balance in can transfer. However, at this point the new vault should not be used yet
    # more than potentially to start fetching from new addresses.
    depositAddrNew = deployAndFetchNative(cf, newVault, Deposit)
    transfer_native(cf, newVault, cf.ALICE, TEST_AMNT)

    # Old vault can still operate
    depositAddr = deployAndFetchNative(cf, cf.vault, Deposit)
    transfer_native(cf, cf.vault, cf.ALICE, TEST_AMNT)

    # Transfer from oldVault to new Vault - unclear if we want to transfer all the balance
    transfer_native(cf, cf.vault, newVault, cf.vault.balance() / 2)
    assert cf.vault.balance() == totalFunds / 2
    assert newVault.balance() == totalFunds / 2

    # Old vault still functions
    cf.SAFEKEEPER.transfer(depositAddr, TEST_AMNT)
    fetchToken(cf, cf.vault, depositAddr, token)
    transfer_native(cf, cf.vault, cf.ALICE, TEST_AMNT)

    # Time where fetchs (and maybe transfers) still can be done from the oldVault
    chain.sleep(DAY)

    # Transfer all the remaining funds to new Vault
    transfer_native(cf, cf.vault, newVault, cf.vault.balance())
    assert newVault.balance() == totalFunds
    assert cf.vault.balance() == 0

    cf.SAFEKEEPER.transfer(depositAddrNew, TEST_AMNT)
    fetchToken(cf, cf.vault, depositAddr, token)
    transfer_native(cf, newVault, cf.ALICE, TEST_AMNT)
    assert newVault.balance() == totalFunds


## Update process StateChainGateway:
# Deploy new StateChainGateway and begin witnessing any new fundings.
# Pause all register redemption signature generation on the State Chain (~7days)
# Wait 7 days for all currently pending redemptions to expire or be executed
# At some point stop witnessing funding calls to old StateChainGateway (on state chain)
# Generate a special redemption sig to move all FLIP to the new State Chain Gateway and register it
# After the REDEMPTION_DELAY, execute the special redemption sig - all FLIP is transferred
# Transfer issuer rights to the new StateChainGateway
@given(
    # adding extra +5 to make up for differences between time.time() and chain time
    st_expiryTimeDiff=strategy(
        "uint", min_value=REDEMPTION_DELAY + 5, max_value=7 * DAY
    ),
    st_sender=strategy("address"),
)
def test_upgrade_StateChainGateway(
    cf,
    StateChainGateway,
    st_expiryTimeDiff,
    st_sender,
    KeyManager,
    FLIP,
    DeployerStateChainGateway,
):
    (_, newStateChainGateway) = deploy_new_stateChainGateway(
        st_sender,
        KeyManager,
        StateChainGateway,
        FLIP,
        DeployerStateChainGateway,
        cf.keyManager.address,
        cf.flip.address,
        MIN_FUNDING,
        REDEMPTION_DELAY,
    )

    # Last register redemption before stopping state's chain redemption signature registry
    nodeID = JUNK_HEX
    expiryTime = getChainTime() + st_expiryTimeDiff
    redemptionAmount = 123 * E_18
    registerRedemptionTest(
        cf,
        cf.stateChainGateway,
        nodeID,
        MIN_FUNDING,
        redemptionAmount,
        cf.DENICE,
        expiryTime,
    )

    chain.sleep(REDEMPTION_DELAY)

    # Execute pending redemption
    initialFlipBalance = cf.flip.balanceOf(cf.DENICE)
    cf.stateChainGateway.executeRedemption(nodeID, {"from": cf.ALICE})
    finalFlipBalance = cf.flip.balanceOf(cf.DENICE)
    assert finalFlipBalance - initialFlipBalance == redemptionAmount
    assert cf.stateChainGateway.getPendingRedemption(nodeID) == NULL_CLAIM

    chain.sleep(7 * DAY - REDEMPTION_DELAY)

    # Generate redemption to move all FLIP to new stateChainGateway
    totalFlipFunded = cf.flip.balanceOf(cf.stateChainGateway)
    expiryTime = getChainTime() + st_expiryTimeDiff
    redemptionAmount = totalFlipFunded
    registerRedemptionTest(
        cf,
        cf.stateChainGateway,
        nodeID,
        MIN_FUNDING,
        redemptionAmount,
        newStateChainGateway,
        expiryTime,
    )

    chain.sleep(REDEMPTION_DELAY)

    assert cf.flip.balanceOf(newStateChainGateway) == 0
    assert cf.flip.balanceOf(cf.stateChainGateway) == totalFlipFunded
    cf.stateChainGateway.executeRedemption(nodeID, {"from": cf.ALICE})
    assert cf.flip.balanceOf(newStateChainGateway) == totalFlipFunded
    assert cf.flip.balanceOf(cf.stateChainGateway) == 0

    # Check that redemptions can be registered and executed in the new StateChainGateway
    registerRedemptionTest(
        cf,
        newStateChainGateway,
        nodeID,
        MIN_FUNDING,
        redemptionAmount,
        cf.DENICE,
        getChainTime() + (REDEMPTION_DELAY * 2),
    )
    chain.sleep(REDEMPTION_DELAY)
    newStateChainGateway.executeRedemption(nodeID, {"from": cf.ALICE})

    signed_call_cf(
        cf,
        cf.stateChainGateway.updateFlipIssuer,
        newStateChainGateway.address,
        False,
        sender=cf.BOB,
    )
    assert cf.flip.getIssuer() == newStateChainGateway.address
