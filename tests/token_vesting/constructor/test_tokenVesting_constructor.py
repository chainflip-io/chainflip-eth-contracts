from consts import *
import time
from brownie import reverts
from shared_tests_tokenVesting import *

start = time.time()
cliff = start + int(YEAR/2)
end = start + YEAR

def test_tokenVesting_constructor_cliff(addrs, TokenVesting, cf):

    with reverts("TokenVest: invalid staking contract cliff"):
        addrs.DEPLOYER.deploy(
                TokenVesting,
                addrs.INVESTOR,
                addrs.REVOKER,
                REVOCABLE,
                start,
                cliff,
                end,
                STAKABLE,
                cf.stakeManager
            )

    tv = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        addrs.REVOKER,
        REVOCABLE,
        start,
        cliff,
        end,
        NON_STAKABLE,
        cf.stakeManager
    )
    check_state(tv, cf, addrs.INVESTOR, addrs.REVOKER, True, cliff, end, False, cf.stakeManager, 0)

    valid_staking_cliff = end

    tv = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        addrs.REVOKER,
        REVOCABLE,
        start,
        valid_staking_cliff,
        end,
        STAKABLE,
        cf.stakeManager
    )
    check_state(tv, cf, addrs.INVESTOR, addrs.REVOKER, True, valid_staking_cliff, end, True, cf.stakeManager, 0)


def test_tokenVesting_constructor_rev_beneficiary(addrs, TokenVesting, cf):
    with reverts("TokenVest: beneficiary_ is the zero address"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            ZERO_ADDR,
            addrs.REVOKER,
            REVOCABLE,
            start,
            cliff,
            end,
            STAKABLE,
            cf.stakeManager
        )


def test_tokenVesting_constructor_rev_revoker(addrs, TokenVesting, cf):
    with reverts("TokenVest: revoker_ is the zero address"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            ZERO_ADDR,
            REVOCABLE,
            start,
            cliff,
            end,
            STAKABLE,
            cf.stakeManager
        )


def test_tokenVesting_constructor_rev_start(addrs, TokenVesting, cf):
    with reverts("TokenVest: start_ is 0"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            REVOCABLE,
            0,
            cliff,
            end,
            STAKABLE,
            cf.stakeManager
        )


def test_tokenVesting_constructor_rev_cliff_0(addrs, TokenVesting, cf):
    with reverts("TokenVest: start_ isn't before cliff_"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            REVOCABLE,
            start,
            0,
            end,
            STAKABLE,
            cf.stakeManager
        )


def test_tokenVesting_constructor_rev_start_not_before_cliff(addrs, TokenVesting, cf):
    with reverts("TokenVest: start_ isn't before cliff_"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            REVOCABLE,
            start,
            start,
            end,
            STAKABLE,
            cf.stakeManager
        )


def test_tokenVesting_constructor_rev_end_0(addrs, TokenVesting, cf):
    with reverts("TokenVest: cliff_ after end_"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            REVOCABLE,
            start,
            cliff,
            0,
            STAKABLE,
            cf.stakeManager
        )


def test_tokenVesting_constructor_rev_cliff_not_before_end(addrs, TokenVesting, cf):
    with reverts("TokenVest: cliff_ after end_"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            REVOCABLE,
            start,
            cliff,
            cliff - 1,
            STAKABLE,
            cf.stakeManager
        )


def test_tokenVesting_constructor_rev_end_before_now(addrs, TokenVesting, cf):
    with reverts("TokenVest: final time is before current time"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            REVOCABLE,
            start - (YEAR*2),
            cliff - (YEAR*2),
            end - (YEAR*2),
            STAKABLE,
            cf.stakeManager
        )


def test_tokenVesting_constructor_rev_stakeManager(addrs, TokenVesting):
    with reverts("TokenVest: stakeManager_ is the zero address"):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            REVOCABLE,
            start,
            cliff,
            end,
            STAKABLE,
            ZERO_ADDR
        )