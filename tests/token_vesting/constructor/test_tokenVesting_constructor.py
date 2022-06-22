from consts import *
import time
from brownie import reverts
from shared_tests_tokenVesting import *

start = time.time()
cliff = start + int(YEAR / 2)
end = start + YEAR


def test_tokenVesting_constructor_cliff(addrs, TokenVesting, cf):

    with reverts(REV_MSG_INVALID_CLIFF):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            REVOCABLE,
            cliff,
            end,
            STAKABLE,
            cf.stakeManager,
        )

    tv = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        addrs.REVOKER,
        REVOCABLE,
        cliff,
        end,
        NON_STAKABLE,
        cf.stakeManager,
    )
    check_state(
        tv,
        cf,
        addrs.INVESTOR,
        addrs.REVOKER,
        True,
        cliff,
        end,
        False,
        cf.stakeManager,
        0,
    )

    valid_staking_cliff = end

    tv = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        addrs.REVOKER,
        REVOCABLE,
        valid_staking_cliff,
        end,
        STAKABLE,
        cf.stakeManager,
    )
    check_state(
        tv,
        cf,
        addrs.INVESTOR,
        addrs.REVOKER,
        True,
        valid_staking_cliff,
        end,
        True,
        cf.stakeManager,
        0,
    )


def test_tokenVesting_constructor_rev_beneficiary(addrs, TokenVesting, cf):
    with reverts(REV_MSG_INVALID_BENEFICIARY):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            ZERO_ADDR,
            addrs.REVOKER,
            REVOCABLE,
            cliff,
            end,
            STAKABLE,
            cf.stakeManager,
        )


def test_tokenVesting_constructor_rev_revoker(addrs, TokenVesting, cf):
    with reverts(REV_MSG_INVALID_REVOKER):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            ZERO_ADDR,
            REVOCABLE,
            cliff,
            end,
            STAKABLE,
            cf.stakeManager,
        )


def test_tokenVesting_constructor_rev_cliff_0(addrs, TokenVesting, cf):
    with reverts(REV_MSG_CLIFF_BEFORE_START):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            REVOCABLE,
            0,
            end,
            STAKABLE,
            cf.stakeManager,
        )


def test_tokenVesting_constructor_rev_end_0(addrs, TokenVesting, cf):
    with reverts(REV_MSG_CLIFF_AFTER_END):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            REVOCABLE,
            cliff,
            0,
            STAKABLE,
            cf.stakeManager,
        )


def test_tokenVesting_constructor_rev_cliff_not_before_end(addrs, TokenVesting, cf):
    with reverts(REV_MSG_CLIFF_AFTER_END):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            REVOCABLE,
            cliff,
            cliff - 1,
            STAKABLE,
            cf.stakeManager,
        )


def test_tokenVesting_constructor_rev_end_before_now(addrs, TokenVesting, cf):
    with reverts(REV_MSG_INVALID_FINAL_TIME):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            REVOCABLE,
            cliff - (YEAR * 2),
            end - (YEAR * 2),
            STAKABLE,
            cf.stakeManager,
        )


def test_tokenVesting_constructor_rev_stakeManager(addrs, TokenVesting):
    with reverts(REV_MSG_INVALID_STAKEMANAGER):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            REVOCABLE,
            cliff,
            end,
            STAKABLE,
            ZERO_ADDR,
        )
