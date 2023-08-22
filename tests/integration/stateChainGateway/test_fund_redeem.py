from consts import *
from shared_tests import *
from brownie import reverts, web3, chain
from utils import *


def test_registerRedemption_fund_executeRedemption_fund_registerRedemption_executeRedemption(
    cf,
):
    receiver = cf.DENICE

    nodeID1 = web3.toHex(1)
    fundAmount1 = MIN_FUNDING * 3
    expiryTime1 = getChainTime() + (REDEMPTION_DELAY * 2)
    redemptionAmount1 = 12345 * E_18

    nodeID2 = web3.toHex(2)
    fundAmount2 = MIN_FUNDING * 7
    expiryTime2 = getChainTime() + (REDEMPTION_DELAY * 3)
    redemptionAmount2 = redemptionAmount1 * 2

    # Register redemption
    registerRedemptionTest(
        cf,
        cf.stateChainGateway,
        nodeID1,
        MIN_FUNDING,
        redemptionAmount1,
        cf.DENICE,
        expiryTime1,
        cf.ALICE,
    )

    # Redemptioning before enough time passed should revert
    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stateChainGateway.executeRedemption(nodeID1, {"from": cf.ALICE})

    chain.sleep(REDEMPTION_DELAY + 5)

    # 1st fund
    cf.flip.approve(cf.stateChainGateway.address, fundAmount1, {"from": cf.ALICE})
    fundTx1 = cf.stateChainGateway.fundStateChainAccount(
        nodeID1, fundAmount1, {"from": cf.ALICE}
    )
    fundTest(cf, 0, nodeID1, MIN_FUNDING, fundTx1, fundAmount1)

    # Execute redemption
    execRedemptionTx1 = cf.stateChainGateway.executeRedemption(
        nodeID1, {"from": cf.ALICE}
    )

    # Check things that should've changed
    assert cf.stateChainGateway.getPendingRedemption(nodeID1) == NULL_CLAIM

    assert (
        cf.flip.balanceOf(cf.stateChainGateway)
        == fundAmount1 - redemptionAmount1 + GATEWAY_INITIAL_BALANCE
    )
    assert execRedemptionTx1.events["RedemptionExecuted"][0].values() == [
        nodeID1,
        redemptionAmount1,
    ]
    assert cf.flip.balanceOf(receiver) == redemptionAmount1
    # Check things that shouldn't have changed
    assert cf.stateChainGateway.getMinimumFunding() == MIN_FUNDING

    # 2nd fund
    cf.flip.approve(cf.stateChainGateway.address, fundAmount2, {"from": cf.BOB})
    fundTx2 = cf.stateChainGateway.fundStateChainAccount(
        nodeID2, fundAmount2, {"from": cf.BOB}
    )

    fundTest(
        cf,
        fundAmount1 - redemptionAmount1,
        nodeID2,
        MIN_FUNDING,
        fundTx2,
        fundAmount2,
    )

    # Executing the 1st redemption again should revert
    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stateChainGateway.executeRedemption(nodeID1, {"from": cf.ALICE})

    # Register 2nd redemption
    registerRedemptionTest(
        cf,
        cf.stateChainGateway,
        nodeID2,
        MIN_FUNDING,
        redemptionAmount2,
        cf.DENICE,
        expiryTime2,
        ZERO_ADDR,
    )

    chain.sleep(REDEMPTION_DELAY + 5)

    # Executing the 1st redemption again should revert
    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stateChainGateway.executeRedemption(nodeID1, {"from": cf.ALICE})

    # Execute 2nd redemption
    execRedemptionTx2 = cf.stateChainGateway.executeRedemption(
        nodeID2, {"from": cf.ALICE}
    )

    # Check things that should've changed
    assert cf.stateChainGateway.getPendingRedemption(nodeID2) == NULL_CLAIM

    assert (
        cf.flip.balanceOf(cf.stateChainGateway)
        == fundAmount1
        - redemptionAmount1
        + fundAmount2
        - redemptionAmount2
        + GATEWAY_INITIAL_BALANCE
    )
    assert execRedemptionTx2.events["RedemptionExecuted"][0].values() == [
        nodeID2,
        redemptionAmount2,
    ]
    assert cf.flip.balanceOf(receiver) == redemptionAmount1 + redemptionAmount2
    # Check things that shouldn't have changed

    assert cf.stateChainGateway.getMinimumFunding() == MIN_FUNDING

    # Executing the 1st redemption again should revert
    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stateChainGateway.executeRedemption(nodeID1, {"from": cf.ALICE})

    # Executing the 2nd redemption again should revert
    with reverts(REV_MSG_NOT_ON_TIME):
        cf.stateChainGateway.executeRedemption(nodeID2, {"from": cf.ALICE})
