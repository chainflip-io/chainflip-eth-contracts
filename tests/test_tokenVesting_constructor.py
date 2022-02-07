from consts import *
import time
from brownie import reverts


start = time.time()
cliff = start + int(YEAR/2)
end = start + YEAR


def test_tokenVesting_constructor(addrs, TokenVesting, mockSM, token):
    tv = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        addrs.REVOKER,
        True,
        start,
        cliff,
        end,
        True,
        mockSM
    )

    assert tv.beneficiary() == addrs.INVESTOR
    assert tv.revoker() == addrs.REVOKER
    assert tv.revocable() == True
    assert tv.cliff() == cliff
    assert tv.end() == end
    assert tv.canStake() == True
    assert tv.stakeManager() == mockSM
    assert tv.released(token) == 0
    assert tv.revoked(token) == 0


def test_tokenVesting_constructor_rev_beneficiary(addrs, TokenVesting, mockSM, token):
    with reverts("TokenVesting: beneficiary_ is the zero address"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            ZERO_ADDR,
            addrs.REVOKER,
            True,
            start,
            cliff,
            end,
            True,
            mockSM
        )


def test_tokenVesting_constructor_rev_revoker(addrs, TokenVesting, mockSM, token):
    with reverts("TokenVesting: revoker_ is the zero address"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            ZERO_ADDR,
            True,
            start,
            cliff,
            end,
            True,
            mockSM
        )


def test_tokenVesting_constructor_rev_start(addrs, TokenVesting, mockSM, token):
    with reverts("TokenVesting: start_ is 0"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            True,
            0,
            cliff,
            end,
            True,
            mockSM
        )


def test_tokenVesting_constructor_rev_cliff_0(addrs, TokenVesting, mockSM, token):
    with reverts("TokenVesting: start_ isn't before cliff_"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            True,
            start,
            0,
            end,
            True,
            mockSM
        )


def test_tokenVesting_constructor_rev_start_not_before_cliff(addrs, TokenVesting, mockSM, token):
    with reverts("TokenVesting: start_ isn't before cliff_"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            True,
            start,
            start,
            end,
            True,
            mockSM
        )


def test_tokenVesting_constructor_rev_end_0(addrs, TokenVesting, mockSM, token):
    with reverts("TokenVesting: cliff_ isn't before end_"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            True,
            start,
            cliff,
            0,
            True,
            mockSM
        )


def test_tokenVesting_constructor_rev_cliff_not_before_end(addrs, TokenVesting, mockSM, token):
    with reverts("TokenVesting: cliff_ isn't before end_"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            True,
            start,
            cliff,
            cliff,
            True,
            mockSM
        )


def test_tokenVesting_constructor_rev_end_before_now(addrs, TokenVesting, mockSM, token):
    with reverts("TokenVesting: final time is before current time"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            True,
            start - (YEAR*2),
            cliff - (YEAR*2),
            end - (YEAR*2),
            True,
            mockSM
        )


def test_tokenVesting_constructor_rev_stakeManager(addrs, TokenVesting, mockSM, token):
    with reverts("TokenVesting: stakeManager_ is the zero address"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            True,
            start,
            cliff,
            end,
            True,
            ZERO_ADDR
        )