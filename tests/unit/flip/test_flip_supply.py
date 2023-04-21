from consts import *
from brownie.test import given, strategy
from brownie import reverts, chain
from utils import *
from shared_tests import *

# NOTE: We want to test mint/burn in isolation from the rest of the contracts
# so we will pass the issuer rights to an address for testing purposes. We do
# this instead of deploying a fresh flip contract as this is closer to what can
# happen in production.


def update_issuer(cf, new_issuer):
    signed_call_cf(cf, cf.stakeManager.updateFlipIssuer, new_issuer)


@given(
    st_amount=strategy("uint256", exclude=0, max_value=TEST_AMNT),
    st_issuer=strategy("address"),
)
def test_mint(cf, st_amount, st_issuer):
    update_issuer(cf, st_issuer)
    iniBalsAlice = cf.flip.balanceOf(cf.ALICE)
    iniTotalSupply = cf.flip.totalSupply()
    tx = cf.flip.mint(cf.ALICE, st_amount, {"from": st_issuer})
    assert cf.flip.balanceOf(cf.ALICE) == iniBalsAlice + st_amount
    assert tx.events["Transfer"].values() == [ZERO_ADDR, cf.ALICE, st_amount]
    assert cf.flip.totalSupply() == iniTotalSupply + st_amount


@given(
    st_amount=strategy("uint256", exclude=0, max_value=TEST_AMNT),
    st_issuer=strategy("address"),
)
def test_burn(cf, st_amount, st_issuer):
    update_issuer(cf, st_issuer)
    iniBalsAlice = cf.flip.balanceOf(cf.ALICE)
    iniTotalSupply = cf.flip.totalSupply()
    tx = cf.flip.burn(cf.ALICE, st_amount, {"from": st_issuer})
    assert cf.flip.balanceOf(cf.ALICE) == iniBalsAlice - st_amount
    assert tx.events["Transfer"].values() == [cf.ALICE, ZERO_ADDR, st_amount]
    assert cf.flip.totalSupply() == iniTotalSupply - st_amount


def test_issue_rev_zeroAddress(cf):
    update_issuer(cf, cf.ALICE)

    # Reverts inside the ERC20 contract
    with reverts("ERC20: mint to the zero address"):
        cf.flip.mint(ZERO_ADDR, JUNK_INT, {"from": cf.ALICE})
    with reverts("ERC20: burn from the zero address"):
        cf.flip.burn(ZERO_ADDR, JUNK_INT, {"from": cf.ALICE})


def test_issue_zeroAmount(cf):
    update_issuer(cf, cf.ALICE)

    iniBals = cf.flip.balanceOf(NON_ZERO_ADDR)

    tx = cf.flip.mint(NON_ZERO_ADDR, 0, {"from": cf.ALICE})
    assert cf.flip.balanceOf(NON_ZERO_ADDR) == iniBals
    assert tx.events["Transfer"].values() == [ZERO_ADDR, NON_ZERO_ADDR, 0]
    tx = cf.flip.burn(NON_ZERO_ADDR, 0, {"from": cf.ALICE})
    assert cf.flip.balanceOf(NON_ZERO_ADDR) == iniBals
    assert tx.events["Transfer"].values() == [NON_ZERO_ADDR, ZERO_ADDR, 0]


@given(
    st_sender=strategy("address"), st_amount=strategy("uint256", max_value=TEST_AMNT)
)
def test_issue_rev_notStakeManager(cf, st_sender, st_amount):

    with reverts(REV_MSG_FLIP_ISSUER):
        cf.flip.mint(NON_ZERO_ADDR, st_amount, {"from": st_sender})

    with reverts(REV_MSG_FLIP_ISSUER):
        cf.flip.burn(NON_ZERO_ADDR, st_amount, {"from": st_sender})
