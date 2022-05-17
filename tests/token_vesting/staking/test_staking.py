from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy


@given(
    st_nodeID=strategy("uint", exclude=0),
    st_amount=strategy("uint256", max_value=MAX_TEST_STAKE),
)
def test_stake_nonstakable(addrs, tokenVestingNoStaking, st_nodeID, st_amount):

    tv, start, cliff, end, total = tokenVestingNoStaking

    st_nodeID = web3.toHex(st_nodeID)

    with reverts(REV_MSG_CANNOT_STAKE):
        tx = tv.stake(st_nodeID, st_amount, {"from": addrs.INVESTOR})


@given(
    st_nodeID=strategy("uint", exclude=0),
    st_amount=strategy("uint256", max_value=MAX_TEST_STAKE * 2),
)
def test_stake(addrs, tokenVestingStaking, st_nodeID, st_amount, cf):

    tv, start, cliff, end, total = tokenVestingStaking

    st_nodeID = web3.toHex(st_nodeID)

    if st_amount < MIN_STAKE:
        with reverts(REV_MSG_MIN_STAKE):
            tx = tv.stake(st_nodeID, st_amount, {"from": addrs.INVESTOR})
    elif st_amount > cf.flip.balanceOf(tv):
        with reverts("ERC20: transfer amount exceeds balance"):
            tx = tv.stake(st_nodeID, st_amount, {"from": addrs.INVESTOR})
    else:
        tx = tv.stake(st_nodeID, st_amount, {"from": addrs.INVESTOR})

        assert tx.events["Staked"][0].values() == (st_nodeID, st_amount, tv, tv)


def test_stake_rev_beneficiary(a, addrs, tokenVestingStaking):
    tv, start, cliff, end, total = tokenVestingStaking

    for ad in a:
        if ad != addrs.INVESTOR:
            with reverts(REV_MSG_NOT_BENEFICIARY):
                tv.stake(5, 10, {"from": ad})
