from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy


def test_release_rev_no_tokens(addrs, token, tokenVesting):
    tv, start, cliff, end, total = tokenVesting

    with reverts(REV_MSG_NO_TOKENS):
        tv.release(token, {'from': addrs.INVESTOR})


@given(sleepTime=strategy('uint256', max_value=YEAR*2))
def test_release(addrs, token, mockSM, tokenVesting, maths, sleepTime):
    tv, start, cliff, end, total = tokenVesting

    assert token.balanceOf(addrs.INVESTOR) == 0

    chain.sleep(sleepTime)

    if chain.time() < cliff:
        with reverts(REV_MSG_NO_TOKENS):
            tv.release(token, {'from': addrs.INVESTOR})
    else:
        tx = tv.release(token, {'from': addrs.INVESTOR})

        newlyReleased = maths.simulateRelease(total, tx.timestamp, start, end) if tx.timestamp < end else total
        assert token.balanceOf(addrs.INVESTOR) == newlyReleased
        assert tv.released(token) == newlyReleased
        assert tx.events["TokensReleased"][0].values() == (token, newlyReleased)
        # Shouldn't've changed
        assert tv.beneficiary() == addrs.INVESTOR
        assert tv.revoker() == addrs.REVOKER
        assert tv.revocable() == True
        assert tv.cliff() == cliff
        assert tv.end() == end
        assert tv.canStake() == True
        assert tv.stakeManager() == mockSM
        assert tv.revoked(token) == 0


def test_release_all(addrs, token, mockSM, tokenVesting, maths):
    tv, start, cliff, end, total = tokenVesting

    assert token.balanceOf(addrs.INVESTOR) == 0

    chain.sleep(YEAR + QUARTER_YEAR)
    tx = tv.release(token, {'from': addrs.INVESTOR})

    assert token.balanceOf(addrs.INVESTOR) == total
    assert tv.released(token) == total
    assert tx.events["TokensReleased"][0].values() == (token, total)
    # Shouldn't've changed
    assert tv.beneficiary() == addrs.INVESTOR
    assert tv.revoker() == addrs.REVOKER
    assert tv.revocable() == True
    assert tv.cliff() == cliff
    assert tv.end() == end
    assert tv.canStake() == True
    assert tv.stakeManager() == mockSM
    assert tv.revoked(token) == 0


def test_release_twice(addrs, token, mockSM, tokenVesting, maths):
    tv, start, cliff, end, total = tokenVesting

    assert token.balanceOf(addrs.INVESTOR) == 0

    chain.sleep(QUARTER_YEAR)
    tx1 = tv.release(token, {'from': addrs.INVESTOR})

    newlyReleased1 = maths.simulateRelease(total, tx1.timestamp, start, end)
    assert token.balanceOf(addrs.INVESTOR) == newlyReleased1
    assert tv.released(token) == newlyReleased1
    assert tx1.events["TokensReleased"][0].values() == (token, newlyReleased1)
    # Shouldn't've changed
    assert tv.beneficiary() == addrs.INVESTOR
    assert tv.revoker() == addrs.REVOKER
    assert tv.revocable() == True
    assert tv.cliff() == cliff
    assert tv.end() == end
    assert tv.canStake() == True
    assert tv.stakeManager() == mockSM
    assert tv.revoked(token) == 0

    chain.sleep(QUARTER_YEAR)
    tx2 = tv.release(token, {'from': addrs.INVESTOR})

    newlyReleased2 = maths.simulateRelease(total, tx2.timestamp, start, end) - newlyReleased1
    assert token.balanceOf(addrs.INVESTOR) == newlyReleased1 + newlyReleased2
    assert tv.released(token) == newlyReleased1 + newlyReleased2
    assert tx2.events["TokensReleased"][0].values() == (token, newlyReleased2)
    # Shouldn't've changed
    assert tv.beneficiary() == addrs.INVESTOR
    assert tv.revoker() == addrs.REVOKER
    assert tv.revocable() == True
    assert tv.cliff() == cliff
    assert tv.end() == end
    assert tv.canStake() == True
    assert tv.stakeManager() == mockSM
    assert tv.revoked(token) == 0
