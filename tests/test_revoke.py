from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy


@given(sleepTime=strategy('uint256', max_value=YEAR*2))
def test_revoke(addrs, token, mockSM, tokenVesting, maths, sleepTime):
    tv, start, cliff, end, total = tokenVesting

    assert token.balanceOf(addrs.INVESTOR) == 0
    assert token.balanceOf(addrs.REVOKER) == 0

    chain.sleep(sleepTime)

    tx = tv.revoke(token, {'from': addrs.REVOKER})

    if tx.timestamp < cliff:
        releasable = 0
    else:
        releasable = maths.simulateRelease(total, tx.timestamp, start, end) if tx.timestamp < end else total
    revokedAmount = total - releasable
    assert token.balanceOf(addrs.REVOKER) == revokedAmount
    assert token.balanceOf(tv) == total - revokedAmount
    assert tx.events["TokenVestingRevoked"][0].values() == [token]
    # Shouldn't've changed
    assert tv.released(token) == 0
    assert token.balanceOf(addrs.INVESTOR) == 0
    assert tv.beneficiary() == addrs.INVESTOR
    assert tv.revoker() == addrs.REVOKER
    assert tv.revocable() == True
    assert tv.cliff() == cliff
    assert tv.end() == end
    assert tv.canStake() == True
    assert tv.stakeManager() == mockSM
    assert tv.revoked(token) == True


def test_revoke_rev_revoker(a, addrs, token, tokenVesting):
    tv, start, cliff, end, total = tokenVesting

    for ad in a:
        if ad != addrs.REVOKER:
            with reverts("TokenVesting: not the revoker"):
                tv.revoke(token, {'from': ad})


def test_revoke_rev_revokable(addrs, token, mockSM, TokenVesting):
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
        mockSM
    )

    with reverts("TokenVesting: cannot revoke"):
        tv.revoke(token, {'from': addrs.REVOKER})


def test_revoke_rev_revoked(a, addrs, token, tokenVesting):
    tv, start, cliff, end, total = tokenVesting

    tv.revoke(token, {'from': addrs.REVOKER})

    with reverts("TokenVesting: token already revoked"):
        tv.revoke(token, {'from': addrs.REVOKER})