from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy


@given(
    st_nodeID=strategy("uint", exclude=0),
    st_amount=strategy("uint256", max_value=MAX_TEST_FUND),
)
def test_fund_nonstakable(addrs, tokenVestingNoStaking, st_nodeID, st_amount):

    tv, cliff, end, total = tokenVestingNoStaking

    st_nodeID = web3.toHex(st_nodeID)

    with reverts(REV_MSG_CANNOT_STAKE):
        tx = tv.fundStateChainAccount(st_nodeID, st_amount, {"from": addrs.INVESTOR})


@given(
    st_nodeID=strategy("uint", exclude=0),
    st_amount=strategy("uint256", max_value=MAX_TEST_FUND * 2),
)
def test_fundStateChainAccount(addrs, tokenVestingStaking, st_nodeID, st_amount, cf):

    tv, cliff, end, total = tokenVestingStaking

    st_nodeID = web3.toHex(st_nodeID)

    if st_amount < MIN_FUNDING:
        with reverts(REV_MSG_MIN_FUNDING):
            tx = tv.fundStateChainAccount(
                st_nodeID, st_amount, {"from": addrs.INVESTOR}
            )
    elif st_amount > cf.flip.balanceOf(tv):
        with reverts("ERC20: transfer amount exceeds balance"):
            tx = tv.fundStateChainAccount(
                st_nodeID, st_amount, {"from": addrs.INVESTOR}
            )
    else:
        tx = tv.fundStateChainAccount(st_nodeID, st_amount, {"from": addrs.INVESTOR})

        assert tx.events["Funded"][0].values() == (st_nodeID, st_amount, tv)


def test_fund_rev_beneficiary(a, addrs, tokenVestingStaking):
    tv, cliff, end, total = tokenVestingStaking

    for ad in a:
        if ad != addrs.INVESTOR:
            with reverts(REV_MSG_NOT_BENEFICIARY):
                tv.fundStateChainAccount(5, 10, {"from": ad})
