from consts import *
from brownie.test import given, strategy
from brownie import reverts
from utils import *
from shared_tests import *


def test_updateFlipSupply(cf):

    cf.flip.approve(cf.stateChainGateway.address, MIN_FUNDING, {"from": cf.ALICE})
    cf.stateChainGateway.fundStateChainAccount(
        JUNK_HEX, MIN_FUNDING, NON_ZERO_ADDR, {"from": cf.ALICE}
    )

    assert (
        cf.flip.balanceOf(cf.stateChainGateway) == MIN_FUNDING + GATEWAY_INITIAL_BALANCE
    )
    assert cf.stateChainGateway.getLastSupplyUpdateBlockNumber() == 0

    stateChainBlockNumber = 1

    tx = signed_call_cf(
        cf,
        cf.stateChainGateway.updateFlipSupply,
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
        sender=cf.ALICE,
    )

    # Balance should be MIN_FUNDING plus the minted delta
    assert (
        cf.flip.balanceOf(cf.stateChainGateway)
        == NEW_TOTAL_SUPPLY_MINT - INIT_SUPPLY + MIN_FUNDING + GATEWAY_INITIAL_BALANCE
    )
    assert (
        cf.stateChainGateway.getLastSupplyUpdateBlockNumber() == stateChainBlockNumber
    )
    assert tx.events["FlipSupplyUpdated"][0].values() == [
        INIT_SUPPLY,
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
    ]

    stateChainBlockNumber = 2

    tx = signed_call_cf(
        cf,
        cf.stateChainGateway.updateFlipSupply,
        INIT_SUPPLY,
        stateChainBlockNumber,
        sender=cf.ALICE,
    )

    # Balance should be MIN_FUNDING as we've just burned all the FLIP we minted
    assert (
        cf.flip.balanceOf(cf.stateChainGateway) == MIN_FUNDING + GATEWAY_INITIAL_BALANCE
    )
    assert (
        cf.stateChainGateway.getLastSupplyUpdateBlockNumber() == stateChainBlockNumber
    )
    assert tx.events["FlipSupplyUpdated"][0].values() == [
        NEW_TOTAL_SUPPLY_MINT,
        INIT_SUPPLY,
        stateChainBlockNumber,
    ]

    # Should not let us update the flip supply with an old block number
    stateChainBlockNumber = 1

    with reverts(REV_MSG_OLD_FLIP_SUPPLY_UPDATE):
        signed_call_cf(
            cf,
            cf.stateChainGateway.updateFlipSupply,
            INIT_SUPPLY,
            stateChainBlockNumber,
            sender=cf.ALICE,
        )


def test_updateFlipSupply_unchangedSupply(cf):

    stateChainGatewayBalanceBefore = cf.flip.balanceOf(cf.stateChainGateway)
    deployerBalanceBefore = cf.flip.balanceOf(cf.SAFEKEEPER)
    totalSupplyBefore = cf.flip.totalSupply()

    assert stateChainGatewayBalanceBefore == GATEWAY_INITIAL_BALANCE
    assert cf.stateChainGateway.getLastSupplyUpdateBlockNumber() == 0

    stateChainBlockNumber = 1

    signed_call_cf(
        cf,
        cf.stateChainGateway.updateFlipSupply,
        cf.flip.totalSupply(),
        stateChainBlockNumber,
        sender=cf.ALICE,
    )

    stateChainGatewayBalanceAfter = cf.flip.balanceOf(cf.stateChainGateway)
    deployerBalanceAfter = cf.flip.balanceOf(cf.SAFEKEEPER)
    totalSupplyAfter = cf.flip.totalSupply()

    assert stateChainGatewayBalanceAfter == stateChainGatewayBalanceBefore
    assert deployerBalanceAfter == deployerBalanceBefore
    assert totalSupplyAfter == totalSupplyBefore


def test_updateFlipSupply_rev(cf):
    stateChainBlockNumber = 1

    with reverts(REV_MSG_NZ_UINT):
        signed_call_cf(
            cf,
            cf.stateChainGateway.updateFlipSupply,
            0,
            stateChainBlockNumber,
            sender=cf.ALICE,
        )

    contractMsgHash = Signer.generate_contractMsgHash(
        cf.stateChainGateway.updateFlipSupply,
        2,
        stateChainBlockNumber,
    )
    msgHash = Signer.generate_msgHash(
        contractMsgHash, nonces, cf.keyManager.address, cf.stateChainGateway.address
    )

    with reverts(REV_MSG_SIG):
        cf.stateChainGateway.updateFlipSupply(
            AGG_SIGNER_1.generate_sigData(msgHash, nonces),
            NEW_TOTAL_SUPPLY_MINT,
            stateChainBlockNumber,
            {"from": cf.ALICE},
        )


def test_updateFlipSupply_constant(cf):
    tx = signed_call_cf(
        cf,
        cf.stateChainGateway.updateFlipSupply,
        cf.flip.totalSupply(),
        1,
        sender=cf.ALICE,
    )
    assert "Transfer" not in tx.events
    assert tx.events["FlipSupplyUpdated"][0].values() == [
        cf.flip.totalSupply(),
        cf.flip.totalSupply(),
        1,
    ]
