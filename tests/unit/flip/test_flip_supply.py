from consts import *
from brownie.test import given, strategy
from brownie import reverts, chain
from utils import *
from shared_tests import *


@given(st_amount=strategy("uint256", exclude=0, max_value=TEST_AMNT))
def test_mint(cf, st_amount):
    # Fund stakeManager via transfer native
    cf.ALICE.transfer(cf.stakeManager.address, 10**18)
    iniBalsAlice = cf.flip.balanceOf(cf.ALICE)
    tx = cf.flip.mint(cf.ALICE, st_amount, {"from": cf.stakeManager.address})
    assert cf.flip.balanceOf(cf.ALICE) == iniBalsAlice + st_amount
    assert tx.events["Transfer"].values() == [ZERO_ADDR, cf.ALICE, st_amount]


@given(st_amount=strategy("uint256", exclude=0, max_value=TEST_AMNT))
def test_burn(cf, st_amount):
    # Fund stakeManager via transfer native
    cf.ALICE.transfer(cf.stakeManager.address, 10**18)
    iniBalsAlice = cf.flip.balanceOf(cf.ALICE)
    tx = cf.flip.burn(cf.ALICE, st_amount, {"from": cf.stakeManager.address})
    assert cf.flip.balanceOf(cf.ALICE) == iniBalsAlice - st_amount
    assert tx.events["Transfer"].values() == [cf.ALICE, ZERO_ADDR, st_amount]


def test_issue_rev_zeroAddress(cf):
    # Fund stakeManager via transfer native
    cf.ALICE.transfer(cf.stakeManager.address, 10**18)

    # Reverts inside the ERC20 contract
    with reverts("ERC20: mint to the zero address"):
        cf.flip.mint(ZERO_ADDR, JUNK_INT, {"from": cf.stakeManager.address})
    with reverts("ERC20: burn from the zero address"):
        cf.flip.burn(ZERO_ADDR, JUNK_INT, {"from": cf.stakeManager.address})


def test_issue_zeroAmount(cf):
    # Fund stakeManager via transfer native
    cf.ALICE.transfer(cf.stakeManager.address, 10**18)

    iniBals = cf.flip.balanceOf(NON_ZERO_ADDR)

    tx = cf.flip.mint(NON_ZERO_ADDR, 0, {"from": cf.stakeManager.address})
    assert cf.flip.balanceOf(NON_ZERO_ADDR) == iniBals
    assert tx.events["Transfer"].values() == [ZERO_ADDR, NON_ZERO_ADDR, 0]
    tx = cf.flip.burn(NON_ZERO_ADDR, 0, {"from": cf.stakeManager.address})
    assert cf.flip.balanceOf(NON_ZERO_ADDR) == iniBals
    assert tx.events["Transfer"].values() == [NON_ZERO_ADDR, ZERO_ADDR, 0]


@given(
    st_sender=strategy("address"), st_amount=strategy("uint256", max_value=TEST_AMNT)
)
def test_issue_rev_notStakeManager(cf, st_sender, st_amount):

    with reverts(REV_MSG_FLIP_STAKEMAN):
        cf.flip.mint(NON_ZERO_ADDR, st_amount, {"from": st_sender})

    with reverts(REV_MSG_FLIP_STAKEMAN):
        cf.flip.burn(NON_ZERO_ADDR, st_amount, {"from": st_sender})
