from consts import *
from brownie.test import given, strategy
from brownie import reverts
from utils import *
from shared_tests import *


def test_updateFlipSupply(cf):

    cf.flip.approve(cf.stakeManager.address, MIN_STAKE, {"from": cf.ALICE})
    cf.stakeManager.stake(JUNK_HEX, MIN_STAKE, NON_ZERO_ADDR, {"from": cf.ALICE})

    assert (
        cf.flip.balanceOf(cf.stakeManager) == MIN_STAKE + STAKEMANAGER_INITIAL_BALANCE
    )
    assert cf.stakeManager.getLastSupplyUpdateBlockNumber() == 0

    stateChainBlockNumber = 1

    tx = signed_call_cf(
        cf,
        cf.stakeManager.updateFlipSupply,
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
        sender=cf.ALICE,
    )

    # Balance should be MIN_STAKE plus the minted delta
    assert (
        cf.flip.balanceOf(cf.stakeManager)
        == NEW_TOTAL_SUPPLY_MINT
        - INIT_SUPPLY
        + MIN_STAKE
        + STAKEMANAGER_INITIAL_BALANCE
    )
    assert cf.stakeManager.getLastSupplyUpdateBlockNumber() == stateChainBlockNumber
    assert tx.events["FlipSupplyUpdated"][0].values() == [
        INIT_SUPPLY,
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
    ]

    stateChainBlockNumber = 2

    tx = signed_call_cf(
        cf,
        cf.stakeManager.updateFlipSupply,
        INIT_SUPPLY,
        stateChainBlockNumber,
        sender=cf.ALICE,
    )

    # Balance should be MIN_STAKE as we've just burned all the FLIP we minted
    assert (
        cf.flip.balanceOf(cf.stakeManager) == MIN_STAKE + STAKEMANAGER_INITIAL_BALANCE
    )
    assert cf.stakeManager.getLastSupplyUpdateBlockNumber() == stateChainBlockNumber
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
            cf.stakeManager.updateFlipSupply,
            INIT_SUPPLY,
            stateChainBlockNumber,
            sender=cf.ALICE,
        )


def test_updateFlipSupply_unchangedSupply(cf):

    stakeManagerBalanceBefore = cf.flip.balanceOf(cf.stakeManager)
    deployerBalanceBefore = cf.flip.balanceOf(cf.SAFEKEEPER)
    totalSupplyBefore = cf.flip.totalSupply()

    assert stakeManagerBalanceBefore == STAKEMANAGER_INITIAL_BALANCE
    assert cf.stakeManager.getLastSupplyUpdateBlockNumber() == 0

    stateChainBlockNumber = 1

    signed_call_cf(
        cf,
        cf.stakeManager.updateFlipSupply,
        cf.flip.totalSupply(),
        stateChainBlockNumber,
        sender=cf.ALICE,
    )

    stakeManagerBalanceAfter = cf.flip.balanceOf(cf.stakeManager)
    deployerBalanceAfter = cf.flip.balanceOf(cf.SAFEKEEPER)
    totalSupplyAfter = cf.flip.totalSupply()

    assert stakeManagerBalanceAfter == stakeManagerBalanceBefore
    assert deployerBalanceAfter == deployerBalanceBefore
    assert totalSupplyAfter == totalSupplyBefore


def test_updateFlipSupply_rev(cf):
    stateChainBlockNumber = 1

    with reverts(REV_MSG_NZ_UINT):
        signed_call_cf(
            cf,
            cf.stakeManager.updateFlipSupply,
            0,
            stateChainBlockNumber,
            sender=cf.ALICE,
        )

    contractMsgHash = Signer.generate_contractMsgHash(
        cf.stakeManager.updateFlipSupply,
        2,
        stateChainBlockNumber,
    )
    msgHash = Signer.generate_msgHash(
        contractMsgHash, nonces, cf.keyManager.address, cf.stakeManager.address
    )

    with reverts(REV_MSG_SIG):
        cf.stakeManager.updateFlipSupply(
            AGG_SIGNER_1.generate_sigData(msgHash, nonces),
            NEW_TOTAL_SUPPLY_MINT,
            stateChainBlockNumber,
            {"from": cf.ALICE},
        )


def test_updateFlipSupply_constant(cf):
    tx = signed_call_cf(
        cf,
        cf.stakeManager.updateFlipSupply,
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
