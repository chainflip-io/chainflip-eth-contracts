from consts import *
from shared_tests import *
from brownie import reverts, web3, chain
from utils import *


def test_registerClaim_fund_executeClaim_fund_registerClaim_executeClaim(cf):
    receiver = cf.DENICE

    nodeID1 = web3.toHex(1)
    fundAmount1 = MIN_FUNDING * 3
    expiryTime1 = getChainTime() + (CLAIM_DELAY * 2)
    claimAmount1 = 12345 * E_18

    nodeID2 = web3.toHex(2)
    fundAmount2 = MIN_FUNDING * 7
    expiryTime2 = getChainTime() + (CLAIM_DELAY * 3)
    claimAmount2 = claimAmount1 * 2

    # Register claim
    registerClaimTest(
        cf,
        cf.stateChainGateway,
        nodeID1,
        MIN_FUNDING,
        claimAmount1,
        cf.DENICE,
        expiryTime1,
    )

    # Claiming before enough time passed should revert
    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stateChainGateway.executeClaim(nodeID1, {"from": cf.ALICE})

    chain.sleep(CLAIM_DELAY + 5)

    # 1st fund
    cf.flip.approve(cf.stateChainGateway.address, fundAmount1, {"from": cf.ALICE})
    fundTx1 = cf.stateChainGateway.fundStateChainAccount(
        nodeID1, fundAmount1, NON_ZERO_ADDR, {"from": cf.ALICE}
    )
    fundTest(cf, 0, nodeID1, MIN_FUNDING, fundTx1, fundAmount1, NON_ZERO_ADDR)

    # Execute claim
    execClaimTx1 = cf.stateChainGateway.executeClaim(nodeID1, {"from": cf.ALICE})

    # Check things that should've changed
    assert cf.stateChainGateway.getPendingClaim(nodeID1) == NULL_CLAIM

    assert (
        cf.flip.balanceOf(cf.stateChainGateway)
        == fundAmount1 - claimAmount1 + GATEWAY_INITIAL_BALANCE
    )
    assert execClaimTx1.events["ClaimExecuted"][0].values() == [nodeID1, claimAmount1]
    assert cf.flip.balanceOf(receiver) == claimAmount1
    # Check things that shouldn't have changed
    assert cf.stateChainGateway.getMinimumFunding() == MIN_FUNDING

    # 2nd fund
    cf.flip.approve(cf.stateChainGateway.address, fundAmount2, {"from": cf.BOB})
    fundTx2 = cf.stateChainGateway.fundStateChainAccount(
        nodeID2, fundAmount2, NON_ZERO_ADDR, {"from": cf.BOB}
    )

    fundTest(
        cf,
        fundAmount1 - claimAmount1,
        nodeID2,
        MIN_FUNDING,
        fundTx2,
        fundAmount2,
        NON_ZERO_ADDR,
    )

    # Executing the 1st claim again should revert
    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stateChainGateway.executeClaim(nodeID1, {"from": cf.ALICE})

    # Register 2nd claim
    registerClaimTest(
        cf,
        cf.stateChainGateway,
        nodeID2,
        MIN_FUNDING,
        claimAmount2,
        cf.DENICE,
        expiryTime2,
    )

    chain.sleep(CLAIM_DELAY + 5)

    # Executing the 1st claim again should revert
    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stateChainGateway.executeClaim(nodeID1, {"from": cf.ALICE})

    # Execute 2nd claim
    execClaimTx2 = cf.stateChainGateway.executeClaim(nodeID2, {"from": cf.ALICE})

    # Check things that should've changed
    assert cf.stateChainGateway.getPendingClaim(nodeID2) == NULL_CLAIM

    assert (
        cf.flip.balanceOf(cf.stateChainGateway)
        == fundAmount1
        - claimAmount1
        + fundAmount2
        - claimAmount2
        + GATEWAY_INITIAL_BALANCE
    )
    assert execClaimTx2.events["ClaimExecuted"][0].values() == [nodeID2, claimAmount2]
    assert cf.flip.balanceOf(receiver) == claimAmount1 + claimAmount2
    # Check things that shouldn't have changed

    assert cf.stateChainGateway.getMinimumFunding() == MIN_FUNDING

    # Executing the 1st claim again should revert
    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stateChainGateway.executeClaim(nodeID1, {"from": cf.ALICE})

    # Executing the 2nd claim again should revert
    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stateChainGateway.executeClaim(nodeID2, {"from": cf.ALICE})
