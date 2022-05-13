from consts import *
from brownie.test import given, strategy
from brownie import reverts, chain
from utils import *


def test_updateFlipSupply(cf):

    cf.flip.approve(cf.stakeManager.address, MIN_STAKE, {"from": cf.ALICE})
    cf.stakeManager.stake(JUNK_HEX, MIN_STAKE, NON_ZERO_ADDR, {"from": cf.ALICE})

    assert (
        cf.flip.balanceOf(cf.stakeManager) == MIN_STAKE + STAKEMANAGER_INITIAL_BALANCE
    )
    assert cf.flip.getLastSupplyUpdateBlockNumber() == 0

    stateChainBlockNumber = 1

    callDataNoSig = cf.flip.updateFlipSupply.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
        cf.stakeManager.address,
    )

    tx = cf.flip.updateFlipSupply(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
        cf.stakeManager.address,
        cf.FR_ALICE,
    )

    # Balance should be MIN_STAKE plus the minted delta
    assert (
        cf.flip.balanceOf(cf.stakeManager)
        == NEW_TOTAL_SUPPLY_MINT
        - INIT_SUPPLY
        + MIN_STAKE
        + STAKEMANAGER_INITIAL_BALANCE
    )
    assert cf.flip.getLastSupplyUpdateBlockNumber() == stateChainBlockNumber
    assert tx.events["FlipSupplyUpdated"][0].values() == [
        INIT_SUPPLY,
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
    ]

    stateChainBlockNumber = 2

    callDataNoSig = cf.flip.updateFlipSupply.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        INIT_SUPPLY,
        stateChainBlockNumber,
        cf.stakeManager.address,
    )

    tx2 = cf.flip.updateFlipSupply(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        INIT_SUPPLY,
        stateChainBlockNumber,
        cf.stakeManager.address,
        cf.FR_ALICE,
    )

    # Balance should be MIN_STAKE as we've just burned all the FLIP we minted
    assert (
        cf.flip.balanceOf(cf.stakeManager) == MIN_STAKE + STAKEMANAGER_INITIAL_BALANCE
    )
    assert cf.flip.getLastSupplyUpdateBlockNumber() == stateChainBlockNumber
    assert tx2.events["FlipSupplyUpdated"][0].values() == [
        NEW_TOTAL_SUPPLY_MINT,
        INIT_SUPPLY,
        stateChainBlockNumber,
    ]

    # Should not let us update the flip supply with an old block number
    stateChainBlockNumber = 1
    callDataNoSig = cf.flip.updateFlipSupply.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        INIT_SUPPLY,
        stateChainBlockNumber,
        cf.stakeManager.address,
    )
    with reverts(REV_MSG_OLD_FLIP_SUPPLY_UPDATE):
        cf.flip.updateFlipSupply(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            INIT_SUPPLY,
            stateChainBlockNumber,
            cf.stakeManager.address,
            cf.FR_ALICE,
        )


def test_updateFlipSupply_unchangedSupply(cf):

    stakeManagerBalanceBefore = cf.flip.balanceOf(cf.stakeManager)
    deployerBalanceBefore = cf.flip.balanceOf(cf.DEPLOYER)
    totalSupplyBefore = cf.flip.totalSupply()

    assert stakeManagerBalanceBefore == STAKEMANAGER_INITIAL_BALANCE
    assert cf.flip.getLastSupplyUpdateBlockNumber() == 0

    stateChainBlockNumber = 1

    callDataNoSig = cf.flip.updateFlipSupply.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        cf.flip.totalSupply(),
        stateChainBlockNumber,
        cf.stakeManager.address,
    )

    tx = cf.flip.updateFlipSupply(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        cf.flip.totalSupply(),
        stateChainBlockNumber,
        cf.stakeManager.address,
        cf.FR_ALICE,
    )

    stakeManagerBalanceAfter = cf.flip.balanceOf(cf.stakeManager)
    deployerBalanceAfter = cf.flip.balanceOf(cf.DEPLOYER)
    totalSupplyAfter = cf.flip.totalSupply()

    assert stakeManagerBalanceAfter == stakeManagerBalanceBefore
    assert deployerBalanceAfter == deployerBalanceBefore
    assert totalSupplyAfter == totalSupplyBefore


def test_updateFlipSupply_rev(cf):
    stateChainBlockNumber = 1

    callDataNoSig = cf.flip.updateFlipSupply.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        0,
        stateChainBlockNumber,
        cf.stakeManager.address,
    )
    with reverts(REV_MSG_NZ_UINT):
        tx = cf.flip.updateFlipSupply(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            0,
            stateChainBlockNumber,
            cf.stakeManager.address,
            cf.FR_ALICE,
        )

    callDataNoSig = cf.flip.updateFlipSupply.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
        ZERO_ADDR,
    )

    with reverts(REV_MSG_NZ_ADDR):
        tx = cf.flip.updateFlipSupply(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            NEW_TOTAL_SUPPLY_MINT,
            stateChainBlockNumber,
            ZERO_ADDR,
            cf.FR_ALICE,
        )

    callDataNoSig = cf.flip.updateFlipSupply.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        2,
        stateChainBlockNumber,
        cf.stakeManager.address,
    )

    with reverts(REV_MSG_MSGHASH):
        tx = cf.flip.updateFlipSupply(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            NEW_TOTAL_SUPPLY_MINT,
            stateChainBlockNumber,
            cf.stakeManager.address,
            cf.FR_ALICE,
        )
