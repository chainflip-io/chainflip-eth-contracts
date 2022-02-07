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