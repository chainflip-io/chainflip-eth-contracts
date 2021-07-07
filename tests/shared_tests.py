from consts import *
from brownie import reverts, chain, web3


# Test with timestamp-1 because of an error where there's a difference of 1s
# because the evm and local clock were out of sync or something... not 100% sure why,
# but some tests occasionally fail for this reason even though they succeed most
# of the time with no changes to the contract or test code
def txTimeTest(time, tx):
    assert time >= tx.timestamp and time <= (tx.timestamp+2)



# ----------Vault----------

# Set keys


def setAggKeyWithAggKey_test(cf):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == GOV_SIGNER_1.getPubDataWith0x()

    callDataNoSig = cf.keyManager.setAggKeyWithAggKey.encode_input(agg_null_sig(), AGG_SIGNER_2.getPubData())
    tx = cf.keyManager.setAggKeyWithAggKey(AGG_SIGNER_1.getSigData(callDataNoSig), AGG_SIGNER_2.getPubData())

    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_2.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == GOV_SIGNER_1.getPubDataWith0x()
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)
    assert tx.events["KeyChange"][0].values() == [True, AGG_SIGNER_1.getPubDataWith0x(), AGG_SIGNER_2.getPubDataWith0x()]


def setAggKeyWithGovKey_test(cf):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == GOV_SIGNER_1.getPubDataWith0x()

    callDataNoSig = cf.keyManager.setAggKeyWithGovKey.encode_input(gov_null_sig(), AGG_SIGNER_2.getPubData())
    tx = cf.keyManager.setAggKeyWithGovKey(GOV_SIGNER_1.getSigData(callDataNoSig), AGG_SIGNER_2.getPubData())

    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_2.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == GOV_SIGNER_1.getPubDataWith0x()
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)
    assert tx.events["KeyChange"][0].values() == [False, AGG_SIGNER_1.getPubDataWith0x(), AGG_SIGNER_2.getPubDataWith0x()]


def setGovKeyWithGovKey_test(cf):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == GOV_SIGNER_1.getPubDataWith0x()

    callDataNoSig = cf.keyManager.setGovKeyWithGovKey.encode_input(gov_null_sig(), GOV_SIGNER_2.getPubData())
    tx = cf.keyManager.setGovKeyWithGovKey(GOV_SIGNER_1.getSigData(callDataNoSig), GOV_SIGNER_2.getPubData())

    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == GOV_SIGNER_2.getPubDataWith0x()
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)
    assert tx.events["KeyChange"][0].values() == [False, GOV_SIGNER_1.getPubDataWith0x(), GOV_SIGNER_2.getPubDataWith0x()]


def setKey_rev_pubKeyX_test(cf, fcn, signer):
    newKey = AGG_SIGNER_2.getPubData()
    newKey[0] = 0
    nullSig = agg_null_sig() if signer.keyID == AGG else gov_null_sig()
    callDataNoSig = fcn.encode_input(nullSig, newKey)
    with reverts(REV_MSG_PUBKEYX):
        fcn(signer.getSigData(callDataNoSig), newKey)


def setKey_rev_nonceTimesGAddr_test(cf, fcn, signer):
    newKey = AGG_SIGNER_2.getPubData()
    nullSig = agg_null_sig() if signer.keyID == AGG else gov_null_sig()
    callDataNoSig = fcn.encode_input(nullSig, newKey)
    sigData = signer.getSigData(callDataNoSig)
    sigData[3] = ZERO_ADDR
    with reverts(REV_MSG_NONCETIMESGADDR_EMPTY):
        fcn(sigData, newKey)


def setKey_rev_msgHash_test(cf, fcn, signer):
    nullSig = agg_null_sig() if signer.keyID == AGG else gov_null_sig()
    callDataNoSig = fcn.encode_input(nullSig, AGG_SIGNER_2.getPubData())
    sigData = signer.getSigData(callDataNoSig)
    sigData[0] += 1
    with reverts(REV_MSG_MSGHASH):
        fcn(sigData, AGG_SIGNER_2.getPubData())


def setKey_rev_sig_test(cf, fcn, signer):
    nullSig = agg_null_sig() if signer.keyID == AGG else gov_null_sig()
    callDataNoSig = fcn.encode_input(nullSig, AGG_SIGNER_2.getPubData())
    sigData = signer.getSigData(callDataNoSig)
    sigData[1] += 1
    with reverts(REV_MSG_SIG):
        fcn(sigData, AGG_SIGNER_2.getPubData())


def isValidSig_test(cf, signer):
    sigData = signer.getSigData(JUNK_HEX_PAD)
    tx = cf.keyManager.isValidSig(sigData, cleanHexStr(sigData[0]), KEYID_TO_NUM[signer.keyID])
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)


def isValidSig_rev_test(cf, signer):
    sigData = signer.getSigData(JUNK_HEX_PAD)
    with reverts(REV_MSG_SIG):
        tx = cf.keyManager.isValidSig(sigData, cleanHexStr(sigData[0]), KEYID_TO_NUM[signer.keyID])


# Hypothesis/brownie doesn't allow you to specifically include values when generating random
# inputs through @given, so this is a common fcn that can be used for `test_claim` and
# similar tests that test specific desired values
# Can't put the if conditions for `amount` in this fcn like in test_claim because
# it's we need to accomodate already having a tx because it's best to test
# `stakedMin` directly
def stakeTest(cf, prevTotal, nodeID, lastMintBlockNum, emissionPerBlock, minStake, tx, amount, returnAddr):
    assert cf.flip.balanceOf(cf.stakeManager) == prevTotal + amount
    assert cf.stakeManager.getTotalStakeInFuture(0) == prevTotal + amount + getInflation(lastMintBlockNum, tx.block_number, EMISSION_PER_BLOCK)
    assert tx.events["Staked"][0].values() == [nodeID, amount, returnAddr]
    assert cf.stakeManager.getLastMintBlockNum() == lastMintBlockNum
    assert cf.stakeManager.getEmissionPerBlock() == emissionPerBlock
    assert cf.stakeManager.getMinimumStake() == minStake


# Hypothesis/brownie doesn't allow you to specifically include values when generating random
# inputs through @given, so this is a common fcn that can be used for `test_claim` and
# similar tests that test specific desired values
def registerClaimTest(cf, prevTx, prevTotal, nodeID, emissionPerBlock, minStake, amount, receiver, expiryTime):
    prevReceiverBal = cf.flip.balanceOf(receiver)
    prevStakeManBal = cf.flip.balanceOf(cf.stakeManager)

    callDataNoSig = cf.stakeManager.registerClaim.encode_input(agg_null_sig(), nodeID, amount, receiver, expiryTime)
    tx = cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), nodeID, amount, receiver, expiryTime)

    startTime = tx.timestamp + CLAIM_DELAY
    inflation = getInflation(prevTx.block_number, tx.block_number, emissionPerBlock)
    # Check things that should've changed
    assert cf.stakeManager.getPendingClaim(nodeID) == (amount, receiver, startTime, expiryTime)
    assert tx.events["ClaimRegistered"][0].values() == (nodeID, amount, receiver, startTime, expiryTime)
    # Check things that shouldn't have changed
    assert cf.flip.balanceOf(receiver) == prevReceiverBal
    assert cf.flip.balanceOf(cf.stakeManager) == prevStakeManBal
    assert cf.stakeManager.getLastMintBlockNum() == prevTx.block_number
    assert cf.stakeManager.getEmissionPerBlock() == emissionPerBlock
    assert cf.stakeManager.getTotalStakeInFuture(0) == prevTotal + inflation
    assert cf.stakeManager.getMinimumStake() == minStake


# # Hypothesis/brownie doesn't allow you to specifically include values when generating random
# # inputs through @given, so this is a common fcn that can be used for `test_claim` and
# # similar tests that test specific desired values
# def registerClaimTest(cf, prevTx, prevTotal, nodeID, emissionPerBlock, minStake, amount, receiver, prevReceiverBal, expiryTime):
#     # Want to calculate inflation 1 block into the future because that's when the tx will execute
#     newLastMintBlockNum = web3.eth.block_number + 1
#     inflation = getInflation(prevTx.block_number, newLastMintBlockNum, emissionPerBlock)
#     maxValidAmount = prevTotal + inflation

#     assert cf.flip.balanceOf(receiver) == prevReceiverBal

#     callDataNoSig = cf.stakeManager.registerClaim.encode_input(agg_null_sig(), receiver, amount, expiryTime, nodeID)

#     if amount == 0:
#         with reverts(REV_MSG_NZ_UINT):
#             cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), receiver, amount, expiryTime, nodeID)
#     else:
#         tx = cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), receiver, amount, expiryTime, nodeID)

#         # Check things that should've changed
#         assert newLastMintBlockNum == tx.block_number
#         assert cf.stakeManager.getLastMintBlockNum() == newLastMintBlockNum
#         assert cf.flip.balanceOf(cf.stakeManager) == maxValidAmount - amount
#         assert cf.stakeManager.getTotalStakeInFuture(0) == maxValidAmount - amount
#         assert tx.events["Claimed"][0].values() == [nodeID, amount]
#         # Check things that shouldn't have changed
#         assert cf.flip.balanceOf(receiver) == prevReceiverBal
#         assert cf.stakeManager.getEmissionPerBlock() == emissionPerBlock
#         assert cf.stakeManager.getMinimumStake() == minStake

