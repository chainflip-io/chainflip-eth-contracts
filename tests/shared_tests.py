from consts import *
from brownie import reverts, chain, web3
from utils import *

# ----------Vault----------


def fetchDepositEth(cf, deployedVault, DepositEth):
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(deployedVault.address, JUNK_HEX_PAD, DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)

    balanceVaultBefore = deployedVault.balance()

    # Sign the tx without a msgHash or sig
    callDataNoSig = deployedVault.fetchDepositEth.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), JUNK_HEX_PAD
    )

    # Fetch the deposit
    balanceBefore = cf.ALICE.balance()
    assert balanceBefore >= TEST_AMNT
    tx = deployedVault.fetchDepositEth(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        JUNK_HEX_PAD,
        {"from": cf.ALICE},
    )
    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
    assert deployedVault.balance() == balanceVaultBefore + TEST_AMNT


# Test transfer function from a vault with funds
def transfer_eth(cf, deployedVault, receiver, amount):
    startBalVault = deployedVault.balance()
    assert startBalVault >= amount
    startBalRecipient = receiver.balance()

    callDataNoSig = deployedVault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), ETH_ADDR, receiver, amount
    )
    tx = deployedVault.transfer(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        ETH_ADDR,
        receiver,
        amount,
    )

    assert deployedVault.balance() - startBalVault == -amount

    # Take into account gas transfer if receiver is the address sending the transfer call (a[0]==cf.DEPLOYER)
    gasSpent = calculateGasTransaction(tx) if receiver == cf.DEPLOYER else 0
    assert receiver.balance() - startBalRecipient == amount - gasSpent


# ----------KeyManager----------

# Set keys


def setAggKeyWithAggKey_test(cf):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == cf.GOVERNOR

    callDataNoSig = cf.keyManager.setAggKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), AGG_SIGNER_2.getPubData()
    )

    balanceBefore = cf.ALICE.balance()
    tx = cf.keyManager.setAggKeyWithAggKey(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        AGG_SIGNER_2.getPubData(),
        {"from": cf.ALICE},
    )
    balanceAfter = cf.ALICE.balance()

    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_2.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == cf.GOVERNOR
    assert tx.events["AggKeySetByAggKey"][0].values() == [
        AGG_SIGNER_1.getPubDataWith0x(),
        AGG_SIGNER_2.getPubDataWith0x(),
    ]


def setKey_rev_newPubKeyX_test(cf):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()

    callDataNoSig = cf.keyManager.setAggKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), BAD_AGG_KEY
    )

    with reverts(REV_MSG_PUB_KEY_X):
        cf.keyManager.setAggKeyWithAggKey(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            BAD_AGG_KEY,
            {"from": cf.ALICE},
        )


def setAggKeyWithGovKey_test(cf):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == cf.GOVERNOR

    tx = cf.keyManager.setAggKeyWithGovKey(
        AGG_SIGNER_2.getPubData(), {"from": cf.GOVERNOR}
    )

    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_2.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == cf.GOVERNOR
    assert tx.events["AggKeySetByGovKey"][0].values() == [
        AGG_SIGNER_1.getPubDataWith0x(),
        AGG_SIGNER_2.getPubDataWith0x(),
    ]


def setGovKeyWithGovKey_test(cf):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == cf.GOVERNOR

    tx = cf.keyManager.setGovKeyWithGovKey(cf.GOVERNOR_2, {"from": cf.GOVERNOR})

    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == cf.GOVERNOR_2
    assert tx.events["GovKeySetByGovKey"][0].values() == [cf.GOVERNOR, cf.GOVERNOR_2]


def setKey_rev_pubKeyX_test(cf, fcn, signer):
    newKey = AGG_SIGNER_2.getPubData()
    newKey[0] = 0
    nullSig = (
        agg_null_sig(cf.keyManager.address, chain.id)
        if signer.keyID == AGG
        else gov_null_sig(cf.keyManager.address, chain.id)
    )
    callDataNoSig = fcn.encode_input(nullSig, newKey)
    with reverts(REV_MSG_PUBKEYX):
        fcn(signer.getSigData(callDataNoSig, cf.keyManager.address), newKey)


def setKey_rev_nonceTimesGAddr_test(cf, fcn, signer):
    newKey = AGG_SIGNER_2.getPubData()
    nullSig = (
        agg_null_sig(cf.keyManager.address, chain.id)
        if signer.keyID == AGG
        else gov_null_sig(cf.keyManager.address, chain.id)
    )
    callDataNoSig = fcn.encode_input(nullSig, newKey)
    sigData = signer.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[3] = ZERO_ADDR
    with reverts(REV_MSG_INPUTS_0):
        fcn(sigData, newKey)


def setKey_rev_msgHash_test(cf, fcn, signer):
    nullSig = (
        agg_null_sig(cf.keyManager.address, chain.id)
        if signer.keyID == AGG
        else gov_null_sig(cf.keyManager.address, chain.id)
    )
    callDataNoSig = fcn.encode_input(nullSig, AGG_SIGNER_2.getPubData())
    sigData = signer.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[2] += 1
    with reverts(REV_MSG_MSGHASH):
        fcn(sigData, AGG_SIGNER_2.getPubData())


def setKey_rev_sig_test(cf, fcn, signer):
    nullSig = (
        agg_null_sig(cf.keyManager.address, chain.id)
        if signer.keyID == AGG
        else gov_null_sig(cf.keyManager.address, chain.id)
    )
    callDataNoSig = fcn.encode_input(nullSig, AGG_SIGNER_2.getPubData())
    sigData = signer.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[3] += 1
    with reverts(REV_MSG_SIG):
        fcn(sigData, AGG_SIGNER_2.getPubData())


def canConsumeKeyNonce_test(cf, signer):
    sigData = signer.getSigData(JUNK_HEX_PAD, cf.keyManager.address)
    tx = cf.keyManager.consumeKeyNonce(sigData, cleanHexStr(sigData[2]))


def canConsumeKeyNonce_rev_test(cf, signer):
    sigData = signer.getSigData(JUNK_HEX_PAD, cf.keyManager.address)
    with reverts(REV_MSG_SIG):
        tx = cf.keyManager.consumeKeyNonce(sigData, cleanHexStr(sigData[2]))


# Hypothesis/brownie doesn't allow you to specifically include values when generating random
# inputs through @given, so this is a common fcn that can be used for `test_claim` and
# similar tests that test specific desired values
# Can't put the if conditions for `amount` in this fcn like in test_claim because
# it's we need to accomodate already having a tx because it's best to test
# `stakedMin` directly
def stakeTest(cf, prevTotal, nodeID, minStake, tx, amount, returnAddr):
    assert (
        cf.flip.balanceOf(cf.stakeManager)
        == prevTotal + amount + STAKEMANAGER_INITIAL_BALANCE
    )
    assert tx.events["Staked"][0].values() == [nodeID, amount, tx.sender, returnAddr]
    assert cf.stakeManager.getMinimumStake() == minStake


# Hypothesis/brownie doesn't allow you to specifically include values when generating random
# inputs through @given, so this is a common fcn that can be used for `test_claim` and
# similar tests that test specific desired values
def registerClaimTest(
    cf, deployedStakeManager, nodeID, minStake, amount, receiver, expiryTime
):
    prevReceiverBal = cf.flip.balanceOf(receiver)
    prevStakeManBal = cf.flip.balanceOf(deployedStakeManager)

    callDataNoSig = deployedStakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        nodeID,
        amount,
        receiver,
        expiryTime,
    )
    tx = deployedStakeManager.registerClaim(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        nodeID,
        amount,
        receiver,
        expiryTime,
    )

    startTime = tx.timestamp + CLAIM_DELAY
    # Check things that should've changed
    assert deployedStakeManager.getPendingClaim(nodeID) == (
        amount,
        receiver,
        startTime,
        expiryTime,
    )
    assert tx.events["ClaimRegistered"][0].values() == (
        nodeID,
        amount,
        receiver,
        startTime,
        expiryTime,
    )
    # Check things that shouldn't have changed
    assert cf.flip.balanceOf(receiver) == prevReceiverBal
    assert cf.flip.balanceOf(deployedStakeManager) == prevStakeManBal
    assert deployedStakeManager.getMinimumStake() == minStake


# Update Whitelisted addresses in the KeyManager - addreses that can consume Nonces
# It requires a list of the current whitelisted addresses and a list of the new ones to whitelist.
# Current whitelist must contain all the whitelisted addresses
# New whitelist must contain the keyManager itself.
def updateCanConsumeKeyNonce(keyManager, currentAddrs, newAddrs):
    callDataNoSig = keyManager.updateCanConsumeKeyNonce.encode_input(
        agg_null_sig(keyManager.address, chain.id), currentAddrs, newAddrs
    )

    keyManager.updateCanConsumeKeyNonce(
        AGG_SIGNER_1.getSigData(callDataNoSig, keyManager.address),
        currentAddrs,
        newAddrs,
    )


# Updates the aggKeyNonceConsumer's reference to the KeyManager. TO be used if the keyManager
# contract is redeployed
def updateKeyManager(aggKeyNonceConsumer, currentkeyManagerAddress, newkeyManager):
    callDataNoSig = aggKeyNonceConsumer.updateKeyManager.encode_input(
        agg_null_sig(currentkeyManagerAddress, chain.id), newkeyManager
    )

    aggKeyNonceConsumer.updateKeyManager(
        AGG_SIGNER_1.getSigData(callDataNoSig, currentkeyManagerAddress), newkeyManager
    )


# Check that Key Agg Nonce consumer can consume nonce
def checkNonceConsumerCanConsume(aggKeyNonceConsumer):
    updateKeyManager(
        aggKeyNonceConsumer,
        aggKeyNonceConsumer.getKeyManager(),
        aggKeyNonceConsumer.getKeyManager(),
    )
