from re import A
from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy

import pytest

@given(sleepTime=strategy('uint256', max_value=YEAR*2))
def test_revoke(addrs, cf, tokenVesting, maths, sleepTime):
    tv, start, cliff, end, total = tokenVesting

    assert cf.flip.balanceOf(addrs.INVESTOR) == 0
    assert cf.flip.balanceOf(addrs.REVOKER) == 0

    chain.sleep(sleepTime)

    tx = tv.revoke(cf.flip, {'from': addrs.REVOKER})

    if tx.timestamp < cliff:
        releasable = 0
    else:
        releasable = maths.simulateRelease(total, tx.timestamp, start, end) if tx.timestamp < end else total
    revokedAmount = total - releasable
 
    # using approx due to comparison limitations with big numbers
    assert float(cf.flip.balanceOf(addrs.REVOKER)) == pytest.approx(revokedAmount)
    assert float(cf.flip.balanceOf(tv)) == pytest.approx(total - revokedAmount)

    
    assert tx.events["TokenVestingRevoked"][0].values() == [cf.flip]
    # Shouldn't've changed
    assert tv.released(cf.flip) == 0
    assert cf.flip.balanceOf(addrs.INVESTOR) == 0
    assert tv.beneficiary() == addrs.INVESTOR
    assert tv.revoker() == addrs.REVOKER
    assert tv.revocable() == True
    assert tv.cliff() == cliff
    assert tv.end() == end
    assert tv.canStake() == True
    assert tv.stakeManager() == cf.stakeManager
    assert tv.revoked(cf.flip) == True


def test_revoke_rev_revoker(a, addrs, cf, tokenVesting):
    tv, start, cliff, end, total = tokenVesting

    for ad in a:
        if ad != addrs.REVOKER:
            with reverts("TokenVesting: not the revoker"):
                tv.revoke(cf.flip, {'from': ad})


def test_revoke_rev_revokable(addrs, cf, TokenVesting):
    start = 1622400000
    cliff = start + QUARTER_YEAR
    end = start + QUARTER_YEAR + YEAR

    tv = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        addrs.REVOKER,
        False,
        start,
        cliff,
        end,
        True,
        cf.stakeManager
    )

    with reverts("TokenVesting: cannot revoke"):
        tv.revoke(cf.flip, {'from': addrs.REVOKER})


def test_revoke_rev_revoked(a, addrs, cf, tokenVesting):
    tv, start, cliff, end, total = tokenVesting

    tv.revoke(cf.flip, {'from': addrs.REVOKER})

    with reverts("TokenVesting: token already revoked"):
        tv.revoke(cf.flip, {'from': addrs.REVOKER})


# @given(
#     amount=strategy('uint256', min_value = MIN_STAKE, max_value=MAX_TEST_STAKE)
# )
def test_revoke_staked(addrs, cf, tokenVesting):
    tv, start, cliff, end, total = tokenVesting
    nodeID1 = web3.toHex(1)

    amount = total

    assert cf.flip.balanceOf(tv) == amount
    assert cf.flip.balanceOf(addrs.INVESTOR) == 0
    assert cf.flip.balanceOf(addrs.REVOKER) == 0

    tx = tv.stake(nodeID1, amount, {'from': addrs.INVESTOR})

    assert tx.events["Staked"][0].values() == (nodeID1, amount, tv, tv)
    assert tx.events["Transfer"][0].values() == (tv, cf.stakeManager, amount)

    assert cf.flip.balanceOf(tv) == 0

    tx = tv.revoke(cf.flip, {'from': addrs.REVOKER})

    # This should refund the whole amount
    assert tx.events["Transfer"][0].values() == (tv, addrs.REVOKER, amount)
    # Currently failing this due to smart contract bug
    #assert tx.events["Transfer"][0].values() == (tv, addrs.REVOKER, 0)

    assert tv.revoked(cf.flip) == True


    sleepTime = cliff
    chain.sleep(sleepTime)

    # We would need to unstake the amount. Quick workaround to do the same thing:
    cf.flip.transfer(tv, amount, {'from': addrs.DEPLOYER})

    # This should either revert or release zero tokens
    tx = tv.release(cf.flip, {'from': addrs.INVESTOR})

    # Currently failing this due to smart contract bug
    assert tx.events["TokensReleased"][0].values() == (cf.flip, 0)
    # Current behaviour
    #assert tx.events["TokensReleased"][0].values() == (cf.flip, amount)
    #assert cf.flip.balanceOf(addrs.INVESTOR) == amount

