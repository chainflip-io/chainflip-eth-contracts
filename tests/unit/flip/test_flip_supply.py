from consts import *
from brownie.test import given, strategy
from brownie import reverts, chain
from utils import *
from shared_tests import *

# NOTE: We want to test mint/burn in isolation from the rest of the contracts
# so we will deploy the FLIP contract separately and set an EOA as the issuer.


def deploy_flip(cf, FLIP, issuer):
    return FLIP.deploy(
        INIT_SUPPLY,
        cf.numGenesisValidators,
        cf.genesisStake,
        cf.ALICE,
        cf.BOB,
        issuer,
        {"from": cf.CHARLIE},
    )


@given(
    st_amount=strategy("uint256", exclude=0, max_value=TEST_AMNT),
)
def test_mint(cf, st_amount, FLIP):
    flip = deploy_flip(cf, FLIP, cf.BOB)
    iniBalsAlice = flip.balanceOf(cf.ALICE)
    iniTotalSupply = flip.totalSupply()
    tx = flip.mint(cf.ALICE, st_amount, {"from": cf.BOB})
    assert flip.balanceOf(cf.ALICE) == iniBalsAlice + st_amount
    assert tx.events["Transfer"].values() == [ZERO_ADDR, cf.ALICE, st_amount]
    assert flip.totalSupply() == iniTotalSupply + st_amount


@given(
    st_amount=strategy("uint256", exclude=0, max_value=TEST_AMNT),
    st_issuer=strategy("address"),
)
def test_burn(cf, st_amount, st_issuer, FLIP):
    flip = deploy_flip(cf, FLIP, st_issuer)
    iniBalsAlice = flip.balanceOf(cf.ALICE)
    iniTotalSupply = flip.totalSupply()
    tx = flip.burn(cf.ALICE, st_amount, {"from": st_issuer})
    assert flip.balanceOf(cf.ALICE) == iniBalsAlice - st_amount
    assert tx.events["Transfer"].values() == [cf.ALICE, ZERO_ADDR, st_amount]
    assert flip.totalSupply() == iniTotalSupply - st_amount


def test_issue_rev_zeroAddress(cf, FLIP):
    flip = deploy_flip(cf, FLIP, cf.ALICE)

    # Reverts inside the ERC20 contract
    with reverts("ERC20: mint to the zero address"):
        flip.mint(ZERO_ADDR, JUNK_INT, {"from": cf.ALICE})
    with reverts("ERC20: burn from the zero address"):
        flip.burn(ZERO_ADDR, JUNK_INT, {"from": cf.ALICE})


def test_issue_zeroAmount(cf, FLIP):
    flip = deploy_flip(cf, FLIP, cf.ALICE)

    iniBals = flip.balanceOf(NON_ZERO_ADDR)

    tx = flip.mint(NON_ZERO_ADDR, 0, {"from": cf.ALICE})
    assert flip.balanceOf(NON_ZERO_ADDR) == iniBals
    assert tx.events["Transfer"].values() == [ZERO_ADDR, NON_ZERO_ADDR, 0]
    tx = flip.burn(NON_ZERO_ADDR, 0, {"from": cf.ALICE})
    assert flip.balanceOf(NON_ZERO_ADDR) == iniBals
    assert tx.events["Transfer"].values() == [NON_ZERO_ADDR, ZERO_ADDR, 0]


@given(
    st_sender=strategy("address"), st_amount=strategy("uint256", max_value=TEST_AMNT)
)
def test_issue_rev_notStateChainGateway(cf, st_sender, st_amount):

    with reverts(REV_MSG_FLIP_ISSUER):
        cf.flip.mint(NON_ZERO_ADDR, st_amount, {"from": st_sender})

    with reverts(REV_MSG_FLIP_ISSUER):
        cf.flip.burn(NON_ZERO_ADDR, st_amount, {"from": st_sender})
