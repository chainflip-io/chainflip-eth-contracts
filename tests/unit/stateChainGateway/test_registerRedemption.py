from consts import *
from shared_tests import *
from brownie import reverts, web3, chain
from brownie.test import given, strategy


@given(
    st_amount=strategy("uint", exclude=0),
    st_funder=strategy("address"),
    # 5s because without a buffer time, the time that the tx actually executes may have changed
    # and make the test fail even though nothing is wrong
    st_expiryTimeDiff=strategy("uint", min_value=5, max_value=365 * DAY),
    st_executor=strategy("address"),
)
def test_registerRedemption_st(
    cf, st_amount, st_funder, st_expiryTimeDiff, st_executor
):
    args = (
        JUNK_HEX,
        st_amount,
        st_funder,
        getChainTime() + REDEMPTION_DELAY + st_expiryTimeDiff,
        st_executor,
    )

    if st_amount == 0:
        with reverts(REV_MSG_NZ_UINT):
            signed_call_cf(cf, cf.stateChainGateway.registerRedemption, *args)
    else:
        registerRedemptionTest(
            cf,
            cf.stateChainGateway,
            JUNK_HEX,
            MIN_FUNDING,
            st_amount,
            st_funder,
            getChainTime() + (2 * REDEMPTION_DELAY),
            st_executor,
        )


# Specific st_amounts that should/shouldn't work


def test_registerRedemption_min_expiryTime(cf):
    registerRedemptionTest(
        cf,
        cf.stateChainGateway,
        JUNK_HEX,
        MIN_FUNDING,
        MIN_FUNDING,
        cf.DENICE,
        getChainTime() + REDEMPTION_DELAY + 5,
        ZERO_ADDR,
    )


def test_registerRedemption_rev_just_under_min_expiryTime(cf, fundedMin):
    _, st_amount = fundedMin

    args = (
        JUNK_HEX,
        st_amount,
        cf.DENICE,
        getChainTime() + REDEMPTION_DELAY - 5,
        NON_ZERO_ADDR,
    )

    with reverts(REV_MSG_EXPIRY_TOO_SOON):
        signed_call_cf(cf, cf.stateChainGateway.registerRedemption, *args)


def test_registerRedemption_redemption_expired(cf, fundedMin):
    _, st_amount = fundedMin
    args = (
        JUNK_HEX,
        st_amount,
        cf.DENICE,
        getChainTime() + REDEMPTION_DELAY + 5,
        cf.ALICE,
    )

    signed_call_cf(cf, cf.stateChainGateway.registerRedemption, *args)

    chain.sleep(REDEMPTION_DELAY + 10)
    registerRedemptionTest(
        cf,
        cf.stateChainGateway,
        JUNK_HEX,
        MIN_FUNDING,
        MIN_FUNDING,
        cf.DENICE,
        getChainTime() + (2 * REDEMPTION_DELAY),
        cf.ALICE,
    )


def test_registerRedemption_rev_redemption_not_expired(cf, fundedMin):
    _, st_amount = fundedMin
    args = (
        JUNK_HEX,
        st_amount,
        cf.DENICE,
        getChainTime() + REDEMPTION_DELAY + 5,
        ZERO_ADDR,
    )

    signed_call_cf(cf, cf.stateChainGateway.registerRedemption, *args)

    with reverts(REV_MSG_CLAIM_EXISTS):
        signed_call_cf(cf, cf.stateChainGateway.registerRedemption, *args)


def test_registerRedemption_rev_nodeID(cf, fundedMin):
    _, st_amount = fundedMin
    args = (0, st_amount, cf.DENICE, getChainTime() + REDEMPTION_DELAY + 5, ZERO_ADDR)

    with reverts(REV_MSG_NZ_BYTES32):
        signed_call_cf(cf, cf.stateChainGateway.registerRedemption, *args)


def test_registerRedemption_rev_st_funder(cf, fundedMin):
    _, st_amount = fundedMin

    with reverts(REV_MSG_NZ_ADDR):
        args = (
            JUNK_HEX,
            st_amount,
            ZERO_ADDR,
            getChainTime() + REDEMPTION_DELAY + 5,
            ZERO_ADDR,
        )
        signed_call_cf(cf, cf.stateChainGateway.registerRedemption, *args)


def test_registerRedemption_rev_sig(cf, fundedMin):
    _, st_amount = fundedMin
    args = (
        JUNK_HEX,
        st_amount,
        cf.DENICE,
        getChainTime() + REDEMPTION_DELAY + 5,
        NON_ZERO_ADDR,
    )

    sigData = AGG_SIGNER_1.getSigDataWithNonces(
        cf.keyManager, cf.stateChainGateway.registerRedemption, nonces, *args
    )

    sigData_modif = sigData[:]
    sigData_modif[0] += 1
    with reverts(REV_MSG_SIG):
        cf.stateChainGateway.registerRedemption(
            sigData_modif, *args, {"from": cf.ALICE}
        )

    sigData_modif = sigData[:]
    sigData_modif[1] += 1
    with reverts(REV_MSG_SIG):
        cf.stateChainGateway.registerRedemption(
            sigData_modif, *args, {"from": cf.ALICE}
        )

    sigData_modif = sigData[:]
    sigData_modif[2] = NON_ZERO_ADDR
    with reverts(REV_MSG_SIG):
        cf.stateChainGateway.registerRedemption(
            sigData_modif, *args, {"from": cf.ALICE}
        )


@given(
    st_sender=strategy("address"),
)
def test_registerRedemption_rev_suspended(cf, fundedMin, st_sender):
    _, st_amount = fundedMin

    cf.stateChainGateway.suspend({"from": cf.GOVERNOR})

    with reverts(REV_MSG_GOV_SUSPENDED):
        args = (
            JUNK_HEX,
            st_amount,
            cf.DENICE,
            getChainTime() + REDEMPTION_DELAY,
            st_sender,
        )
        signed_call_cf(
            cf, cf.stateChainGateway.registerRedemption, *args, sender=st_sender
        )
