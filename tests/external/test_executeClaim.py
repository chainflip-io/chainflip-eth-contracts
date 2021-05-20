from consts import *
from shared_tests import *
from brownie import reverts, web3, chain
from brownie.test import given, strategy


# Need to also register a claim in this since the amounts sent etc depend on registerClaim
# @given(
#     nodeID=strategy('uint', exclude=0),
#     amount=strategy('uint', max_value=MIN_STAKE*2, exclude=0),
#     staker=strategy('address'),
#     expiryTimeDiff=strategy('uint', min_value=CLAIM_DELAY, max_value=2*CLAIM_DELAY),
#     sleepTime=strategy('uint', min_value=5, max_value=3*CLAIM_DELAY)
# )
# def test_executeClaim_rand(cf, stakedMin, nodeID, amount, staker, expiryTimeDiff, sleepTime):
#     assert cf.stakeManager.getPendingClaim(nodeID) == NULL_CLAIM
#     smStartBal = cf.flip.balanceOf(cf.stakeManager)
#     stakerStartBal = cf.flip.balanceOf(staker)

#     expiryTime = chain.time() + expiryTimeDiff + 5
#     args = (nodeID, amount, staker, expiryTime)
#     callDataNoSig = cf.stakeManager.registerClaim.encode_input(NULL_SIG_DATA, *args)
#     tx1 = cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args)
    
#     assert cf.stakeManager.getPendingClaim(nodeID) == (amount, staker, tx1.timestamp + CLAIM_DELAY, expiryTime)
#     assert cf.flip.balanceOf(cf.stakeManager) == smStartBal

#     # Want to calculate inflation 1 block into the future because that's when the tx will execute
#     newLastMintBlockNum = web3.eth.blockNumber + 1
#     inflation = getInflation(cf.stakeManager.tx.block_number, newLastMintBlockNum, EMISSION_PER_BLOCK)
#     maxValidAmount = cf.flip.balanceOf(cf.stakeManager) + inflation

#     chain.sleep(sleepTime)
    
#     if chain.time() < tx1.timestamp + CLAIM_DELAY or chain.time() > expiryTime:
#         with reverts(REV_MSG_NOT_ON_TIME):
#             cf.stakeManager.executeClaim(nodeID)
#     elif amount > maxValidAmount:
#         with reverts(REV_MSG_EXCEED_BAL):
#             cf.stakeManager.executeClaim(nodeID)
#     else:
#         tx = cf.stakeManager.executeClaim(nodeID)
        
#         # Check things that should've changed
#         assert cf.stakeManager.getPendingClaim(nodeID) == NULL_CLAIM
#         assert newLastMintBlockNum == tx.block_number
#         assert cf.stakeManager.getLastMintBlockNum() == newLastMintBlockNum
#         assert cf.flip.balanceOf(cf.stakeManager) == maxValidAmount - amount
#         assert cf.stakeManager.getTotalStakeInFuture(0) == maxValidAmount - amount
#         assert tx.events["ClaimExecuted"][0].values() == [nodeID, amount]
#         assert cf.flip.balanceOf(staker) == stakerStartBal + amount
#         # Check things that shouldn't have changed
#         assert cf.stakeManager.getEmissionPerBlock() == EMISSION_PER_BLOCK
#         assert cf.stakeManager.getMinimumStake() == MIN_STAKE

def test_executeClaim_min_delay(cf, claimRegistered):
    _, claim = claimRegistered
    assert cf.stakeManager.getPendingClaim(JUNK_INT) == claim
    
    # Want to calculate inflation 1 block into the future because that's when the tx will execute
    newLastMintBlockNum = web3.eth.blockNumber + 1
    inflation = getInflation(cf.stakeManager.tx.block_number, newLastMintBlockNum, EMISSION_PER_BLOCK)
    maxValidAmount = cf.flip.balanceOf(cf.stakeManager) + inflation

    chain.sleep(CLAIM_DELAY)
    tx = cf.stakeManager.executeClaim(JUNK_INT)

    # Check things that should've changed
    assert cf.stakeManager.getPendingClaim(JUNK_INT) == NULL_CLAIM
    assert newLastMintBlockNum == tx.block_number
    assert cf.stakeManager.getLastMintBlockNum() == newLastMintBlockNum
    assert cf.flip.balanceOf(cf.stakeManager) == maxValidAmount - claim[0]
    assert cf.stakeManager.getTotalStakeInFuture(0) == maxValidAmount - claim[0]
    assert tx.events["ClaimExecuted"][0].values() == [JUNK_INT, claim[0]]
    assert cf.flip.balanceOf(claim[1]) == claim[0]
    # Check things that shouldn't have changed
    assert cf.stakeManager.getEmissionPerBlock() == EMISSION_PER_BLOCK
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE