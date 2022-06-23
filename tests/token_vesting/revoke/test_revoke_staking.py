from re import A
from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy
from shared_tests_tokenVesting import *

import pytest


@given(st_sleepTime=strategy("uint256", max_value=YEAR * 2))
def test_revoke(addrs, cf, tokenVestingStaking, maths, st_sleepTime):
    tv, cliff, end, total = tokenVestingStaking

    assert cf.flip.balanceOf(addrs.INVESTOR) == 0
    assert cf.flip.balanceOf(addrs.REVOKER) == 0
    revokedAmount = 0

    chain.sleep(st_sleepTime)

    if getChainTime() < cliff:
        tx = tv.revoke(cf.flip, {"from": addrs.REVOKER})
        releasable = 0
    elif getChainTime() >= end:
        with reverts(REV_MSG_VESTING_EXPIRED):
            tv.revoke(cf.flip, {"from": addrs.REVOKER})
        return
    else:
        # Should not happen as cliff == end
        assert False

    revokedAmount = total - releasable

    check_revoked(tv, cf, tx, addrs.REVOKER, revokedAmount, total - revokedAmount)

    # Shouldn't've changed
    check_state(
        tv,
        cf,
        addrs.INVESTOR,
        addrs.REVOKER,
        True,
        cliff,
        end,
        True,
        cf.stakeManager,
        True,
    )
    assert tv.released(cf.flip) == 0
    assert cf.flip.balanceOf(addrs.INVESTOR) == 0
    assert cf.flip.balanceOf(tv) == 0

    # When canStake, no amount is releasable after revoking
    chain.sleep(st_sleepTime)

    with reverts(REV_MSG_FUNDS_REVOKED):
        tv.release(cf.flip, {"from": addrs.INVESTOR})


def test_revoke_rev_revoker(a, addrs, cf, tokenVestingStaking):
    tv, cliff, end, total = tokenVestingStaking

    for ad in a:
        if ad != addrs.REVOKER:
            with reverts(REV_MSG_NOT_REVOKER):
                tv.revoke(cf.flip, {"from": ad})


def test_revoke_rev_revokable(addrs, cf, TokenVesting):
    start = 1622400000
    end = start + QUARTER_YEAR + YEAR
    cliff = end

    tv = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        ZERO_ADDR,
        cliff,
        end,
        STAKABLE,
        cf.stakeManager,
    )

    with reverts(REV_MSG_NOT_REVOKER):
        tv.revoke(cf.flip, {"from": addrs.REVOKER})


def test_revoke_rev_revoked(a, addrs, cf, tokenVestingStaking):
    tv, cliff, end, total = tokenVestingStaking

    tx = tv.revoke(cf.flip, {"from": addrs.REVOKER})

    check_revoked(tv, cf, tx, addrs.REVOKER, total, 0)

    with reverts(REV_MSG_ALREADY_REVOKED):
        tv.revoke(cf.flip, {"from": addrs.REVOKER})

    # No more funds to be retrieved
    assert cf.flip.balanceOf(tv) == 0
    retrieve_revoked_and_check(tv, cf, addrs.REVOKER, 0)


def test_revoke_staked(addrs, cf, tokenVestingStaking):
    tv, cliff, end, total = tokenVestingStaking
    nodeID1 = web3.toHex(1)

    amount = total

    assert cf.flip.balanceOf(tv) == amount
    assert cf.flip.balanceOf(addrs.INVESTOR) == 0
    assert cf.flip.balanceOf(addrs.REVOKER) == 0

    tx = tv.stake(nodeID1, amount, {"from": addrs.INVESTOR})

    assert tx.events["Staked"][0].values() == (nodeID1, amount, tv, tv)
    assert tx.events["Transfer"][0].values() == (tv, cf.stakeManager, amount)

    assert cf.flip.balanceOf(tv) == 0

    tx = tv.revoke(cf.flip, {"from": addrs.REVOKER})

    assert tx.events["Transfer"][0].values() == (tv, addrs.REVOKER, 0)
    assert tv.revoked(cf.flip) == True

    with reverts(REV_MSG_FUNDS_REVOKED):
        tv.release(cf.flip, {"from": addrs.INVESTOR})

    # We would need to unstake the amount. Quick workaround to do the same thing:
    cf.flip.transfer(tv, amount, {"from": addrs.DEPLOYER})

    with reverts(REV_MSG_FUNDS_REVOKED):
        tv.release(cf.flip, {"from": addrs.INVESTOR})

    st_sleepTime = cliff
    chain.sleep(st_sleepTime)

    # In option B, once revoked there is no way to release any funds
    with reverts(REV_MSG_FUNDS_REVOKED):
        tv.release(cf.flip, {"from": addrs.INVESTOR})


@given(
    st_amount=strategy("uint256", min_value=MIN_STAKE, max_value=MAX_TEST_STAKE),
    rewards=strategy("uint256", max_value=MAX_TEST_STAKE),
)
def test_retrieve_revoked_funds_and_rewards(
    addrs, cf, tokenVestingStaking, st_amount, rewards
):
    tv, cliff, end, total = tokenVestingStaking

    cf.flip.approve(cf.stakeManager.address, st_amount, {"from": addrs.INVESTOR})
    tx = tv.stake(1, st_amount, {"from": addrs.INVESTOR})
    tx = tv.revoke(cf.flip, {"from": addrs.REVOKER})

    assert cf.flip.balanceOf(tv) == 0

    with reverts(REV_MSG_NOT_REVOKER):
        tv.retrieveRevokedFunds(cf.flip, {"from": addrs.INVESTOR})

    retrieve_revoked_and_check(tv, cf, addrs.REVOKER, 0)

    # Mimic remaining stake st_amount unstaked
    cf.flip.transfer(tv, st_amount, {"from": addrs.DEPLOYER})
    retrieve_revoked_and_check(tv, cf, addrs.REVOKER, st_amount)

    # Mimic rewards
    cf.flip.transfer(tv, rewards, {"from": addrs.DEPLOYER})

    with reverts(REV_MSG_FUNDS_REVOKED):
        tv.release(cf.flip, {"from": addrs.INVESTOR})

    retrieve_revoked_and_check(tv, cf, addrs.REVOKER, rewards)


# If revoked when staked, we don't get the funds. Then we have to enforce that the beneficiary unstakes it.
# When that happens the beneficiary can't release the funds but they can front-run our retrieveFunds.
def test_stake_revoked_staked(addrs, cf, tokenVestingStaking):
    tv, cliff, end, total = tokenVestingStaking
    test_revoke_staked(addrs, cf, tokenVestingStaking)
    nodeID1 = web3.toHex(1)
    with reverts(REV_MSG_FLIP_REVOKED):
        tv.stake(nodeID1, MAX_TEST_STAKE, {"from": addrs.INVESTOR})
    retrieve_revoked_and_check(tv, cf, addrs.REVOKER, MAX_TEST_STAKE)
