from consts import *
from shared_tests import *
from brownie import reverts, web3, chain
from brownie.test import given, strategy

# Goal is to test upgrading contracts (deploy a new version) except FLIP.


## Update processs KeyManager:
# Deploy new keyManager
# Whitelist current contracts in new KeyManager
# (whitelisting before updating references to ensure contracts can always validate)
# Update all keyManager references
# Dewhitelist contracts in old KeyManager
@given(
    st_sender=strategy("address"),
)
def test_upgrade_keyManager(cf, KeyManager, st_sender):

    # Try initial transfer to later test a replay attack on the newly deployed keyManager
    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), ETH_ADDR, cf.ALICE, TEST_AMNT
    )
    sigdata = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    cf.vault.transfer(
        sigdata,
        ETH_ADDR,
        cf.ALICE,
        TEST_AMNT,
    )

    # Reusing current keyManager aggregateKey for simplicity
    newKeyManager = cf.DEPLOYER.deploy(
        KeyManager, cf.keyManager.getAggregateKey(), cf.gov, cf.COMMUNITY_KEY
    )

    # Reverts if keyManager is not whitelisted
    with reverts(REV_MSG_KEYMANAGER_WHITELIST):
        newKeyManager.setCanConsumeKeyNonce([])

    toWhitelist = [cf.vault, cf.stakeManager, cf.flip, newKeyManager]
    newKeyManager.setCanConsumeKeyNonce(toWhitelist)

    aggKeyNonceConsumers = [cf.vault, cf.stakeManager, cf.flip]
    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        signed_call_cf(cf, aggKeyNonceConsumer.updateKeyManager, newKeyManager)
        assert aggKeyNonceConsumer.getKeyManager() == newKeyManager

    # Remove all whitelist
    # Reverts if keyManager is not whitelisted
    with reverts(REV_MSG_KEYMANAGER_WHITELIST):
        signed_call_cf(
            cf,
            cf.keyManager.updateCanConsumeKeyNonce,
            cf.whitelisted,
            [],
            sender=st_sender,
        )

    signed_call_cf(
        cf,
        cf.keyManager.updateCanConsumeKeyNonce,
        cf.whitelisted,
        [cf.keyManager],
        sender=st_sender,
    )

    for aggKeyNonceConsumer in aggKeyNonceConsumers:
        # Check that messages signed with old keyManager's address revert in the new one
        with reverts(REV_MSG_WRONG_KEYMANADDR):
            signed_call_cf(cf, aggKeyNonceConsumer.updateKeyManager, NON_ZERO_ADDR)

        # Try one validation per contract to check that they can validate
        signed_call_cf(
            cf,
            aggKeyNonceConsumer.updateKeyManager,
            aggKeyNonceConsumer.getKeyManager(),
            keyManager=newKeyManager,
        )

    # Try replay attack using transaction called on the previous keyManager
    # nonce is available on the new keyManager so it relies on signing over the keyManager address
    with reverts(REV_MSG_WRONG_KEYMANADDR):
        cf.vault.transfer(
            sigdata,
            ETH_ADDR,
            cf.ALICE,
            TEST_AMNT,
        )

    # Check that a new transfer works and uses the new keyManager
    currentNonce = nonces[AGG]
    assert newKeyManager.isNonceUsedByAggKey(currentNonce) == False
    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(newKeyManager, chain.id), ETH_ADDR, cf.ALICE, TEST_AMNT
    )
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, newKeyManager)
    cf.vault.transfer(
        sigData,
        ETH_ADDR,
        cf.ALICE,
        TEST_AMNT,
    )
    assert newKeyManager.isNonceUsedByAggKey(currentNonce) == True

    # Try another replay attack
    with reverts(REV_MSG_KEYMANAGER_NONCE):
        cf.vault.transfer(
            sigData,
            ETH_ADDR,
            cf.ALICE,
            TEST_AMNT,
        )


## Update process Vault:
# Deploy new Vault
# Whitelist new Vault. Old vault still needs to be active to be able to fetch active swaps
# Transfer tokens from old Vault to new Vault.
# At the end we will anyway have to do a final transfer from Vault to Vault, so no need to transfer all the balance now.
# Therefore we can still make some swap-transfers from old Vault or we can do them from the new one, whatever is easier for the stateChain
# Once a certain amount of time has passed (no more old vault fetches) we transfer remaining amount to new Vault
# DeWhitelist old Vault, which should have zero balance
@given(
    st_sender=strategy("address"),
)
def test_upgrade_Vault(cf, Vault, DepositEth, st_sender):

    totalFunds = cf.DENICE.balance() / 10
    # Replicate a vault with funds - 1000 ETH
    cf.DENICE.transfer(cf.vault, totalFunds)

    newVault = cf.DEPLOYER.deploy(Vault, cf.keyManager)

    # Check that newly deployed Vault can't validate signatures (not whitelisted yet)
    # Technically we could precomute the deployed address and whitelist it before deployment
    # but that is unnecessary
    with reverts(REV_MSG_WHITELIST):
        args = (ETH_ADDR, cf.ALICE, TEST_AMNT)
        signed_call_cf(cf, newVault.transfer, *args, sender=st_sender)

    # Keep old Vault whitelisted
    currentWhitelist = [cf.vault, cf.stakeManager, cf.flip, cf.keyManager]
    toWhitelist = [cf.vault, cf.stakeManager, cf.flip, cf.keyManager, newVault]

    signed_call_cf(
        cf,
        cf.keyManager.updateCanConsumeKeyNonce,
        currentWhitelist,
        toWhitelist,
        sender=st_sender,
    )

    # Vault can now validate and fetch but it has zero balance so it can't transfer
    tx = signed_call_cf(cf, newVault.transfer, *args, sender=st_sender)

    assert tx.events["TransferFailed"][0].values() == [
        cf.ALICE,
        TEST_AMNT,
        web3.toHex(0),
    ]

    # with a balance in can transfer. However, at this point the new vault should not be used yet
    # more than potentially to start fetching from new addresses.
    fetchDepositEth(cf, newVault, DepositEth)
    transfer_eth(cf, newVault, cf.ALICE, TEST_AMNT)

    # Old vault can still operate
    fetchDepositEth(cf, cf.vault, DepositEth)
    transfer_eth(cf, cf.vault, cf.ALICE, TEST_AMNT)

    # Transfer from oldVault to new Vault - unclear if we want to transfer all the balance
    transfer_eth(cf, cf.vault, newVault, cf.vault.balance() / 2)
    assert cf.vault.balance() == totalFunds / 2
    assert newVault.balance() == totalFunds / 2

    # Old vault still functions
    fetchDepositEth(cf, cf.vault, DepositEth)
    transfer_eth(cf, cf.vault, cf.ALICE, TEST_AMNT)

    # Time where fetchs (and maybe transfers) still can be done from the oldVault
    chain.sleep(DAY)

    # Transfer all the remaining funds to new Vault and dewhitelist
    transfer_eth(cf, cf.vault, newVault, cf.vault.balance())
    assert newVault.balance() == totalFunds
    assert cf.vault.balance() == 0

    currentWhitelist = [cf.vault, cf.stakeManager, cf.flip, cf.keyManager, newVault]
    toWhitelist = [newVault, cf.stakeManager, cf.flip, cf.keyManager]
    signed_call_cf(
        cf,
        cf.keyManager.updateCanConsumeKeyNonce,
        currentWhitelist,
        toWhitelist,
        sender=st_sender,
    )

    # Old Vault cannot validate Signatures anymore
    with reverts(REV_MSG_WHITELIST):
        signed_call_cf(cf, cf.vault.transfer, *args, sender=st_sender)

    fetchDepositEth(cf, newVault, DepositEth)
    transfer_eth(cf, newVault, cf.ALICE, TEST_AMNT)
    assert newVault.balance() == totalFunds


## Update process StakeManager:
# Deploy new StakeManager and whitelist it(and begin witnessing any new stakes)
# Pause all register claim signature generation on the State Chain (~7days)
# Wait 7 days for all currently pending claims to expire or be executed
# At some point stop witnessing stake calls to old StakeManager (on state chain)
# Generate a special claim sig to move all FLIP to the new Stake Manager and register it
# After the CLAIM_DELAY, execute the special claim sig - all FLIP is transfered
# Dewhilist old StakeManager
@given(
    # adding extra +5 to make up for differences between time.time() and chain time
    st_expiryTimeDiff=strategy("uint", min_value=CLAIM_DELAY + 5, max_value=7 * DAY),
    st_sender=strategy("address"),
)
def test_upgrade_StakeManager(cf, StakeManager, st_expiryTimeDiff, st_sender):
    newStakeManager = cf.DEPLOYER.deploy(StakeManager, cf.keyManager, MIN_STAKE)

    with reverts(REV_MSG_STAKEMAN_DEPLOYER):
        newStakeManager.setFlip(cf.flip, {"from": cf.ALICE})

    newStakeManager.setFlip(cf.flip)

    # Keep old StakeManager whitelisted
    currentWhitelist = [cf.vault, cf.stakeManager, cf.flip, cf.keyManager]
    toWhitelist = [cf.vault, cf.stakeManager, cf.flip, cf.keyManager, newStakeManager]
    signed_call_cf(
        cf,
        cf.keyManager.updateCanConsumeKeyNonce,
        currentWhitelist,
        toWhitelist,
        sender=st_sender,
    )

    # Last register claim before stopping state's chain claim signature registry
    nodeID = JUNK_HEX
    expiryTime = getChainTime() + st_expiryTimeDiff
    claimAmount = 123 * E_18
    registerClaimTest(
        cf, cf.stakeManager, nodeID, MIN_STAKE, claimAmount, cf.DENICE, expiryTime
    )

    chain.sleep(CLAIM_DELAY)

    # Execute pending claim
    initialFlipBalance = cf.flip.balanceOf(cf.DENICE)
    cf.stakeManager.executeClaim(nodeID)
    finalFlipBalance = cf.flip.balanceOf(cf.DENICE)
    assert finalFlipBalance - initialFlipBalance == claimAmount
    assert cf.stakeManager.getPendingClaim(nodeID) == NULL_CLAIM

    chain.sleep(7 * DAY - CLAIM_DELAY)

    # Generate claim to move all FLIP to new stakeManager
    totalFlipstaked = cf.flip.balanceOf(cf.stakeManager)
    expiryTime = getChainTime() + st_expiryTimeDiff
    claimAmount = totalFlipstaked
    registerClaimTest(
        cf, cf.stakeManager, nodeID, MIN_STAKE, claimAmount, newStakeManager, expiryTime
    )

    chain.sleep(CLAIM_DELAY)

    assert cf.flip.balanceOf(newStakeManager) == 0
    assert cf.flip.balanceOf(cf.stakeManager) == totalFlipstaked
    cf.stakeManager.executeClaim(nodeID)
    assert cf.flip.balanceOf(newStakeManager) == totalFlipstaked
    assert cf.flip.balanceOf(cf.stakeManager) == 0

    # Dewhitelist old StakeManager
    currentWhitelist = [
        cf.vault,
        cf.stakeManager,
        cf.flip,
        cf.keyManager,
        newStakeManager,
    ]
    toWhitelist = [cf.vault, newStakeManager, cf.flip, cf.keyManager]
    signed_call_cf(
        cf,
        cf.keyManager.updateCanConsumeKeyNonce,
        currentWhitelist,
        toWhitelist,
        sender=st_sender,
    )

    # Check that claims cannot be registered in old StakeManager
    with reverts(REV_MSG_WHITELIST):
        args = (nodeID, claimAmount, cf.DENICE, expiryTime)
        signed_call_cf(cf, cf.stakeManager.registerClaim, *args)

    # Check that claims can be registered and executed in the new StakeManager
    registerClaimTest(
        cf,
        newStakeManager,
        nodeID,
        MIN_STAKE,
        claimAmount,
        cf.DENICE,
        getChainTime() + (CLAIM_DELAY * 2),
    )
    chain.sleep(CLAIM_DELAY)
    newStakeManager.executeClaim(nodeID)
