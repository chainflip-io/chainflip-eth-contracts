from consts import *
import time
from brownie import reverts
from shared_tests_tokenVesting import *

start = time.time()
cliff = start + int(YEAR / 2)
end = start + YEAR


def test_tokenVesting_constructor_cliff(addrs, TokenVesting, cf, addressHolder):

    with reverts(REV_MSG_INVALID_CLIFF):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            cliff,
            end,
            STAKABLE,
            BENEF_TRANSF,
            addressHolder,
        )

    tv = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        addrs.REVOKER,
        cliff,
        end,
        NON_STAKABLE,
        BENEF_TRANSF,
        addressHolder,
    )
    check_state(
        tv,
        cf,
        addrs.INVESTOR,
        addrs.REVOKER,
        addrs.REVOKER != ZERO_ADDR,
        cliff,
        end,
        False,
        True,
        cf.stateChainGateway,
        0,
        addressHolder,
    )

    valid_staking_cliff = end

    tv = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        addrs.REVOKER,
        valid_staking_cliff,
        end,
        STAKABLE,
        BENEF_NON_TRANSF,
        addressHolder,
    )
    check_state(
        tv,
        cf,
        addrs.INVESTOR,
        addrs.REVOKER,
        addrs.REVOKER != ZERO_ADDR,
        valid_staking_cliff,
        end,
        True,
        False,
        cf.stateChainGateway,
        0,
        addressHolder,
    )


def test_tokenVesting_constructor_noRevoker(addrs, TokenVesting, addressHolder):
    addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        ZERO_ADDR,
        end,
        end,
        STAKABLE,
        BENEF_TRANSF,
        addressHolder,
    )


def test_tokenVesting_constructor_rev_beneficiary(addrs, TokenVesting, addressHolder):
    with reverts(REV_MSG_INVALID_BENEFICIARY):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            ZERO_ADDR,
            addrs.REVOKER,
            cliff,
            end,
            STAKABLE,
            BENEF_TRANSF,
            addressHolder,
        )


def test_tokenVesting_constructor_rev_end_0(addrs, TokenVesting, addressHolder):
    with reverts(REV_MSG_CLIFF_AFTER_END):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            cliff,
            0,
            STAKABLE,
            BENEF_NON_TRANSF,
            addressHolder,
        )


def test_tokenVesting_constructor_rev_cliff_not_before_end(
    addrs, TokenVesting, addressHolder
):
    with reverts(REV_MSG_CLIFF_AFTER_END):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            cliff,
            cliff - 1,
            STAKABLE,
            BENEF_TRANSF,
            addressHolder,
        )


def test_tokenVesting_constructor_rev_end_before_now(
    addrs, TokenVesting, addressHolder
):
    with reverts(REV_MSG_INVALID_FINAL_TIME):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            cliff - (YEAR * 2),
            end - (YEAR * 2),
            STAKABLE,
            BENEF_TRANSF,
            addressHolder,
        )


def test_tokenVesting_constructor_rev_stateChainGateway(addrs, TokenVesting):
    with reverts(REV_MSG_INVALID_SCGREF):
        addrs.DEPLOYER.deploy(
            TokenVesting,
            addrs.INVESTOR,
            addrs.REVOKER,
            cliff,
            end,
            STAKABLE,
            BENEF_NON_TRANSF,
            ZERO_ADDR,
        )


def test_tokenVesting_constructor_rev_eoa(addrs, TokenVesting):

    tv = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        addrs.REVOKER,
        end,
        end,
        STAKABLE,
        BENEF_NON_TRANSF,
        NON_ZERO_ADDR,
    )
    # Reference contract is an eoa
    with reverts("Transaction reverted without a reason string"):
        tv.fundStateChainAccount(JUNK_INT, 1, {"from": addrs.INVESTOR})


def test_tokenVesting_constructor_rev_ref_eoa(addrs, TokenVesting, AddressHolder):

    addressHolder = addrs.DEPLOYER.deploy(AddressHolder, addrs.DEPLOYER, NON_ZERO_ADDR)

    tv = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        addrs.REVOKER,
        end,
        end,
        STAKABLE,
        BENEF_TRANSF,
        addressHolder,
    )
    # Reference contract that points to an eoa
    with reverts("Transaction reverted without a reason string"):
        tv.fundStateChainAccount(JUNK_INT, 1, {"from": addrs.INVESTOR})
