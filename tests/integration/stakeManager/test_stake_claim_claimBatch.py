from consts import *
from shared_tests import *
from brownie import reverts


def test_stake_claim_stake_claim(cf, web3):
    nodeID1 = 1
    stakeAmount1 = MIN_STAKE * 3

    claimAmount1 = 12345 * E_18

    nodeID2 = 2
    stakeAmount2 = MIN_STAKE * 7

    claimAmount2 = claimAmount1*2

    receiver = cf.DENICE

    # Unstaking before anything is staked should revert
    tx, inflationRev = registerClaimTest(
        cf,
        web3,
        cf.stakeManager.tx,
        0,
        nodeID1,
        EMISSION_PER_BLOCK,
        MIN_STAKE,
        stakeAmount1,
        receiver,
        0
    )
    assert tx is None
    

    # 1st stake
    stakeTx1 = cf.stakeManager.stake(nodeID1, stakeAmount1, cf.FR_ALICE)

    stakeTest(
        cf,
        0,
        nodeID1,
        cf.stakeManager.tx.block_number,
        EMISSION_PER_BLOCK,
        MIN_STAKE,
        stakeTx1,
        stakeAmount1
    )
    
    # Claim a portion of staked funds
    callDataNoSig = cf.stakeManager.claim.encode_input(NULL_SIG_DATA, nodeID1, receiver, stakeAmount1)

    claimTx1, inflation1 = registerClaimTest(
        cf,
        web3,
        cf.stakeManager.tx,
        stakeAmount1,
        nodeID1,
        EMISSION_PER_BLOCK,
        MIN_STAKE,
        claimAmount1,
        receiver,
        0
    )
    assert claimTx1 is not None

    # 2nd stake
    stakeTx2 = cf.stakeManager.stake(nodeID2, stakeAmount2, cf.FR_BOB)

    stakeTest(
        cf,
        stakeAmount1 - claimAmount1 + inflation1,
        nodeID2,
        claimTx1.block_number,
        EMISSION_PER_BLOCK,
        MIN_STAKE,
        stakeTx2,
        stakeAmount2
    )
    
    # 2nd claim
    claimTx2, inflation2 = registerClaimTest(
        cf,
        web3,
        claimTx1,
        stakeAmount1 - claimAmount1 + inflation1 + stakeAmount2,
        nodeID2,
        EMISSION_PER_BLOCK,
        MIN_STAKE,
        claimAmount2,
        receiver,
        claimAmount1
    )
    assert claimTx2 is not None

    newLastMintBlockNum = web3.eth.blockNumber + 1
    inflation3 = getInflation(claimTx2.block_number, newLastMintBlockNum, EMISSION_PER_BLOCK)
    nodeIDs = [21, 31]
    receivers = [cf.DENICE, cf.DENICE]
    amounts = [MIN_STAKE, 1]
    totalAmount = sum(amounts)

    callDataNoSig = cf.stakeManager.claimBatch.encode_input(NULL_SIG_DATA, nodeIDs, receivers, amounts)
    batchClaimTx = cf.stakeManager.claimBatch(AGG_SIGNER_1.getSigData(callDataNoSig), nodeIDs, receivers, amounts)

    # Check things that should've changed
    assert cf.flip.balanceOf(cf.stakeManager) == stakeAmount1 - claimAmount1 + inflation1 + stakeAmount2 - claimAmount2 + inflation2 + inflation3 - sum(amounts)
    assert cf.stakeManager.getLastMintBlockNum() == batchClaimTx.block_number
    assert cf.stakeManager.getTotalStakeInFuture(0) == stakeAmount1 - claimAmount1 + inflation1 + stakeAmount2 - claimAmount2 + inflation2 + inflation3 - sum(amounts)
    assert batchClaimTx.events["Transfer"][0].values() == [ZERO_ADDR, cf.stakeManager.address, inflation3]
    assert len(batchClaimTx.events["Transfer"]) == len(amounts) + 1
    assert len(batchClaimTx.events["Claimed"]) == len(amounts)
    assert cf.flip.balanceOf(cf.DENICE) == claimAmount1 + claimAmount2 + sum(amounts)
    for i in range(len(receivers)):
        assert batchClaimTx.events["Claimed"][i].values() == [nodeIDs[i], amounts[i]]
    
    # Check things that shouldn't have changed
    assert cf.stakeManager.getEmissionPerBlock() == EMISSION_PER_BLOCK
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE