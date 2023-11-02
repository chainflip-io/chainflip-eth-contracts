from consts import *
import time
from brownie import reverts
from shared_tests_tokenVesting import *

start = time.time()
cliff = start + int(YEAR / 2)
end = cliff + YEAR


def test_tokenVesting_constructor_cliff(
    addrs, TokenVestingNoStaking, TokenVestingStaking, cf, addressHolder
):

    tv = addrs.DEPLOYER.deploy(
        TokenVestingNoStaking,
        addrs.BENEFICIARY,
        addrs.REVOKER,
        cliff,
        end,
        BENEF_TRANSF,
    )
    check_state_noStaking(
        cliff,
        tv,
        addrs.BENEFICIARY,
        addrs.REVOKER,
        addrs.REVOKER != ZERO_ADDR,
        end,
        True,
        False,
    )

    tv = addrs.DEPLOYER.deploy(
        TokenVestingStaking,
        addrs.BENEFICIARY,
        addrs.REVOKER,
        cliff,
        end,
        BENEF_NON_TRANSF,
        addressHolder,
        cf.flip,
    )
    check_state_staking(
        cf.stateChainGateway,
        addressHolder,
        tv,
        cliff,
        addrs.BENEFICIARY,
        addrs.REVOKER,
        addrs.REVOKER != ZERO_ADDR,
        end,
        False,
        False,
    )


def test_tokenVesting_constructor_noRevoker(
    addrs, TokenVestingNoStaking, TokenVestingStaking, addressHolder
):
    addrs.DEPLOYER.deploy(
        TokenVestingNoStaking,
        addrs.BENEFICIARY,
        ZERO_ADDR,
        end,
        end,
        BENEF_TRANSF,
    )
    addrs.DEPLOYER.deploy(
        TokenVestingStaking,
        addrs.BENEFICIARY,
        ZERO_ADDR,
        end,
        end,
        BENEF_TRANSF,
        addressHolder,
        NON_ZERO_ADDR,
    )


def test_tokenVesting_constructor_rev_beneficiary(
    addrs, TokenVestingNoStaking, TokenVestingStaking, addressHolder
):
    with reverts(REV_MSG_NZ_ADDR):
        addrs.DEPLOYER.deploy(
            TokenVestingNoStaking,
            ZERO_ADDR,
            addrs.REVOKER,
            cliff,
            end,
            BENEF_TRANSF,
        )
    with reverts(REV_MSG_NZ_ADDR):
        addrs.DEPLOYER.deploy(
            TokenVestingStaking,
            ZERO_ADDR,
            addrs.REVOKER,
            cliff,
            end,
            BENEF_TRANSF,
            addressHolder,
            NON_ZERO_ADDR,
        )

    with reverts(REV_MSG_NZ_ADDR):
        addrs.DEPLOYER.deploy(
            TokenVestingStaking,
            NON_ZERO_ADDR,
            addrs.REVOKER,
            cliff,
            end,
            BENEF_TRANSF,
            addressHolder,
            ZERO_ADDR,
        )


def test_tokenVesting_constructor_rev_end_0(
    addrs, TokenVestingNoStaking, TokenVestingStaking
):
    with reverts(REV_MSG_CLIFF_AFTER_END):
        addrs.DEPLOYER.deploy(
            TokenVestingNoStaking,
            addrs.BENEFICIARY,
            addrs.REVOKER,
            cliff,
            0,
            BENEF_NON_TRANSF,
        )
    with reverts(REV_MSG_NZ_ADDR):
        addrs.DEPLOYER.deploy(
            TokenVestingStaking,
            NON_ZERO_ADDR,
            addrs.REVOKER,
            cliff,
            0,
            BENEF_TRANSF,
            NON_ZERO_ADDR,
            ZERO_ADDR,
        )


def test_tokenVesting_constructor_rev_cliff_not_before_end(
    addrs, TokenVestingNoStaking, TokenVestingStaking
):
    with reverts(REV_MSG_CLIFF_AFTER_END):
        addrs.DEPLOYER.deploy(
            TokenVestingNoStaking,
            addrs.BENEFICIARY,
            addrs.REVOKER,
            cliff,
            cliff - 1,
            BENEF_TRANSF,
        )

    with reverts(REV_MSG_CLIFF_AFTER_END):
        addrs.DEPLOYER.deploy(
            TokenVestingStaking,
            NON_ZERO_ADDR,
            addrs.REVOKER,
            cliff,
            cliff - 1,
            BENEF_TRANSF,
            NON_ZERO_ADDR,
            NON_ZERO_ADDR,
        )


def test_tokenVesting_constructor_rev_cliff_before_now(
    addrs, TokenVestingNoStaking, TokenVestingStaking
):
    with reverts(REV_MSG_INVALID_VESTING_TIME):
        addrs.DEPLOYER.deploy(
            TokenVestingNoStaking,
            addrs.BENEFICIARY,
            addrs.REVOKER,
            cliff - (YEAR * 2),
            end - (YEAR * 2),
            BENEF_TRANSF,
        )

    with reverts(REV_MSG_INVALID_VESTING_TIME):
        addrs.DEPLOYER.deploy(
            TokenVestingStaking,
            NON_ZERO_ADDR,
            addrs.REVOKER,
            cliff - (YEAR * 2),
            end - (YEAR * 2),
            BENEF_TRANSF,
            NON_ZERO_ADDR,
            NON_ZERO_ADDR,
        )


def test_tokenVesting_constructor_rev_stateChainGateway(addrs, TokenVestingStaking):
    with reverts(REV_MSG_NZ_ADDR):
        addrs.DEPLOYER.deploy(
            TokenVestingStaking,
            addrs.BENEFICIARY,
            addrs.REVOKER,
            cliff,
            end,
            BENEF_NON_TRANSF,
            ZERO_ADDR,
            NON_ZERO_ADDR,
        )


def test_tokenVesting_constructor_rev_eoa(addrs, TokenVestingStaking):

    tv = addrs.DEPLOYER.deploy(
        TokenVestingStaking,
        addrs.BENEFICIARY,
        addrs.REVOKER,
        cliff,
        end,
        BENEF_NON_TRANSF,
        NON_ZERO_ADDR,
        NON_ZERO_ADDR,
    )
    # Reference contract is an eoa
    with reverts("Transaction reverted without a reason string"):
        tv.fundStateChainAccount(JUNK_INT, 1, {"from": addrs.BENEFICIARY})
