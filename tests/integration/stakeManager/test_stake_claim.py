from consts import *
from shared_tests import *
from brownie import reverts


def test_stake_claim_stake_claim(cf, web3):
    nodeID1 = 1
    stakeAmount1 = MIN_STAKE * 3
    staker1 = cf.ALICE

    claimAmount1 = 12345 * E_18

    nodeID2 = 2
    stakeAmount2 = MIN_STAKE * 7
    staker1 = cf.BOB

    claimAmount2 = claimAmount1*2

    receiver = cf.DENICE

    # Unstaking before anything is staked should revert
    tx, inflationRev = claimTest(
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

    claimTx1, inflation1 = claimTest(
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
    claimTx2, inflation2 = claimTest(
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