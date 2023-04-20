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
        cf.stakeManager.address,
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
        cf.stakeManager.address,
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
            cf.stakeManager.address,
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
        cf.stakeManager.address,
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
            cf.stakeManager.address,
            sender=cf.ALICE,
        )

    with reverts(REV_MSG_NZ_ADDR):
        signed_call_cf(
            cf,
            cf.stakeManager.updateFlipSupply,
            NEW_TOTAL_SUPPLY_MINT,
            stateChainBlockNumber,
            ZERO_ADDR,
            sender=cf.ALICE,
        )

    contractMsgHash = Signer.generate_contractMsgHash(
        cf.stakeManager.updateFlipSupply,
        2,
        stateChainBlockNumber,
        cf.stakeManager.address,
    )
    msgHash = Signer.generate_msgHash(
        contractMsgHash, nonces, cf.keyManager.address, cf.stakeManager.address
    )

    with reverts(REV_MSG_SIG):
        cf.stakeManager.updateFlipSupply(
            AGG_SIGNER_1.generate_sigData(msgHash, nonces),
            NEW_TOTAL_SUPPLY_MINT,
            stateChainBlockNumber,
            cf.stakeManager.address,
            {"from": cf.ALICE},
        )


def test_updateFlipSupply_constant(cf):
    tx = signed_call_cf(
        cf,
        cf.stakeManager.updateFlipSupply,
        cf.flip.totalSupply(),
        1,
        NON_ZERO_ADDR,
        sender=cf.ALICE,
    )
    assert "Transfer" not in tx.events
    assert tx.events["FlipSupplyUpdated"][0].values() == [
        cf.flip.totalSupply(),
        cf.flip.totalSupply(),
        1,
    ]


# This will never happen, just verifying the logic
# TODO: Unclear what the behaviour should be - tbd. We might hardcode
# address(this) in the StakeManager contract.
@given(
    st_holder=strategy("address"),
    st_receiver=strategy("address"),
    st_amount=strategy("uint256", min_value=1, max_value=TEST_AMNT),
)
def test_updateFlippySupply_transfer(cf, st_holder, st_amount, st_receiver):

    # Fund flip holder
    cf.flip.transfer(st_holder, TEST_AMNT, {"from": cf.SAFEKEEPER})

    stateChainBlockNumber = 1
    new_supply = cf.flip.totalSupply() - st_amount

    iniBals_holder = cf.flip.balanceOf(st_holder)

    tx = signed_call_cf(
        cf,
        cf.stakeManager.updateFlipSupply,
        new_supply,
        stateChainBlockNumber,
        st_holder,
        sender=cf.ALICE,
    )

    assert tx.events["FlipSupplyUpdated"][0].values() == [
        new_supply + st_amount,
        new_supply,
        stateChainBlockNumber,
    ]

    finalBals_holder = cf.flip.balanceOf(st_holder)
    assert finalBals_holder == iniBals_holder - st_amount

    stateChainBlockNumber += 1

    tx = signed_call_cf(
        cf,
        cf.stakeManager.updateFlipSupply,
        new_supply,
        stateChainBlockNumber,
        st_holder,
        sender=cf.BOB,
    )

    iniBals_receiver = cf.flip.balanceOf(st_receiver)

    stateChainBlockNumber += 1

    tx = signed_call_cf(
        cf,
        cf.stakeManager.updateFlipSupply,
        new_supply + st_amount,
        stateChainBlockNumber,
        st_receiver,
        sender=cf.ALICE,
    )

    assert tx.events["FlipSupplyUpdated"][0].values() == [
        new_supply,
        new_supply + st_amount,
        stateChainBlockNumber,
    ]

    assert cf.flip.balanceOf(st_receiver) == iniBals_receiver + st_amount
    if st_holder != st_receiver:
        assert finalBals_holder == cf.flip.balanceOf(st_holder)
