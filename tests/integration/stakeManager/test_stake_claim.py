from consts import *
from shared_tests import *
from brownie import reverts, web3, chain
from utils import *


def test_registerClaim_stake_executeClaim_stake_registerClaim_executeClaim(cf):
    receiver = cf.DENICE

    nodeID1 = web3.toHex(1)
    stakeAmount1 = MIN_STAKE * 3
    expiryTime1 = getChainTime() + (CLAIM_DELAY * 2)
    claimAmount1 = 12345 * E_18

    nodeID2 = web3.toHex(2)
    stakeAmount2 = MIN_STAKE * 7
    expiryTime2 = getChainTime() + (CLAIM_DELAY * 3)
    claimAmount2 = claimAmount1 * 2

    # Register claim
    registerClaimTest(
        cf, cf.stakeManager, nodeID1, MIN_STAKE, claimAmount1, cf.DENICE, expiryTime1
    )

    # Claiming before enough time passed should revert
    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stakeManager.executeClaim(nodeID1)

    chain.sleep(CLAIM_DELAY + 5)

    # 1st stake
    cf.flip.approve(cf.stakeManager.address, stakeAmount1, cf.FR_ALICE)
    stakeTx1 = cf.stakeManager.stake(nodeID1, stakeAmount1, NON_ZERO_ADDR, cf.FR_ALICE)
    stakeTest(cf, 0, nodeID1, MIN_STAKE, stakeTx1, stakeAmount1, NON_ZERO_ADDR)

    # Execute claim
    execClaimTx1 = cf.stakeManager.executeClaim(nodeID1)

    # Check things that should've changed
    assert cf.stakeManager.getPendingClaim(nodeID1) == NULL_CLAIM

    assert (
        cf.flip.balanceOf(cf.stakeManager)
        == stakeAmount1 - claimAmount1 + STAKEMANAGER_INITIAL_BALANCE
    )
    assert execClaimTx1.events["ClaimExecuted"][0].values() == [nodeID1, claimAmount1]
    assert cf.flip.balanceOf(receiver) == claimAmount1
    # Check things that shouldn't have changed
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE

    # 2nd stake
    cf.flip.approve(cf.stakeManager.address, stakeAmount2, cf.FR_BOB)
    stakeTx2 = cf.stakeManager.stake(nodeID2, stakeAmount2, NON_ZERO_ADDR, cf.FR_BOB)

    stakeTest(
        cf,
        stakeAmount1 - claimAmount1,
        nodeID2,
        MIN_STAKE,
        stakeTx2,
        stakeAmount2,
        NON_ZERO_ADDR,
    )

    # Executing the 1st claim again should revert
    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stakeManager.executeClaim(nodeID1)

    # Register 2nd claim
    registerClaimTest(
        cf, cf.stakeManager, nodeID2, MIN_STAKE, claimAmount2, cf.DENICE, expiryTime2
    )

    chain.sleep(CLAIM_DELAY + 5)

    # Executing the 1st claim again should revert
    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stakeManager.executeClaim(nodeID1)

    # Execute 2nd claim
    execClaimTx2 = cf.stakeManager.executeClaim(nodeID2)

    # Check things that should've changed
    assert cf.stakeManager.getPendingClaim(nodeID2) == NULL_CLAIM

    assert (
        cf.flip.balanceOf(cf.stakeManager)
        == stakeAmount1
        - claimAmount1
        + stakeAmount2
        - claimAmount2
        + STAKEMANAGER_INITIAL_BALANCE
    )
    assert execClaimTx2.events["ClaimExecuted"][0].values() == [nodeID2, claimAmount2]
    assert cf.flip.balanceOf(receiver) == claimAmount1 + claimAmount2
    # Check things that shouldn't have changed

    assert cf.stakeManager.getMinimumStake() == MIN_STAKE

    # Executing the 1st claim again should revert
    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stakeManager.executeClaim(nodeID1)

    # Executing the 2nd claim again should revert
    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stakeManager.executeClaim(nodeID2)
