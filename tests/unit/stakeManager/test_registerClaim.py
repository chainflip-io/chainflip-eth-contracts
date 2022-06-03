from consts import *
from shared_tests import *
from brownie import reverts, web3, chain
from brownie.test import given, strategy


@given(
    st_amount=strategy("uint", exclude=0),
    st_staker=strategy("address"),
    # 5s because without a buffer time, the time that the tx actually executes may have changed
    # and make the test fail even though nothing is wrong
    st_expiryTimeDiff=strategy("uint", min_value=5, max_value=365 * DAY),
)
def test_registerClaim_st_amount_rand(
    cf, stakedMin, st_amount, st_staker, st_expiryTimeDiff
):
    args = (
        JUNK_HEX,
        st_amount,
        st_staker,
        getChainTime() + CLAIM_DELAY + st_expiryTimeDiff,
    )

    if st_amount == 0:
        with reverts(REV_MSG_NZ_UINT):
            signed_call_cf(cf, cf.stakeManager.registerClaim, *args)
    else:
        registerClaimTest(
            cf,
            cf.stakeManager,
            JUNK_HEX,
            MIN_STAKE,
            st_amount,
            st_staker,
            getChainTime() + (2 * CLAIM_DELAY),
        )


# Specific st_amounts that should/shouldn't work


def test_registerClaim_min_expiryTime(cf, stakedMin):
    registerClaimTest(
        cf,
        cf.stakeManager,
        JUNK_HEX,
        MIN_STAKE,
        MIN_STAKE,
        cf.DENICE,
        getChainTime() + CLAIM_DELAY + 5,
    )


def test_registerClaim_rev_just_under_min_expiryTime(cf, stakedMin):
    _, st_amount = stakedMin

    args = (JUNK_HEX, st_amount, cf.DENICE, getChainTime() + CLAIM_DELAY - 5)

    with reverts(REV_MSG_EXPIRY_TOO_SOON):
        signed_call_cf(cf, cf.stakeManager.registerClaim, *args)


def test_registerClaim_claim_expired(cf, stakedMin):
    _, st_amount = stakedMin
    args = (JUNK_HEX, st_amount, cf.DENICE, getChainTime() + CLAIM_DELAY + 5)

    signed_call_cf(cf, cf.stakeManager.registerClaim, *args)

    chain.sleep(CLAIM_DELAY + 10)
    registerClaimTest(
        cf,
        cf.stakeManager,
        JUNK_HEX,
        MIN_STAKE,
        MIN_STAKE,
        cf.DENICE,
        getChainTime() + (2 * CLAIM_DELAY),
    )


def test_registerClaim_rev_claim_not_expired(cf, stakedMin):
    _, st_amount = stakedMin
    args = (JUNK_HEX, st_amount, cf.DENICE, getChainTime() + CLAIM_DELAY + 5)

    signed_call_cf(cf, cf.stakeManager.registerClaim, *args)

    with reverts(REV_MSG_CLAIM_EXISTS):
        signed_call_cf(cf, cf.stakeManager.registerClaim, *args)


def test_registerClaim_rev_nodeID(cf, stakedMin):
    _, st_amount = stakedMin
    args = (0, st_amount, cf.DENICE, getChainTime() + CLAIM_DELAY + 5)

    with reverts(REV_MSG_NZ_BYTES32):
        signed_call_cf(cf, cf.stakeManager.registerClaim, *args)


def test_registerClaim_rev_st_staker(cf, stakedMin):
    _, st_amount = stakedMin

    with reverts(REV_MSG_NZ_ADDR):
        args = (JUNK_HEX, st_amount, ZERO_ADDR, getChainTime() + CLAIM_DELAY + 5)
        signed_call_cf(cf, cf.stakeManager.registerClaim, *args)


def test_registerClaim_rev_msgHash(cf, stakedMin):
    _, st_amount = stakedMin
    args = (JUNK_HEX, st_amount, cf.DENICE, getChainTime() + CLAIM_DELAY + 5)
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[2] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.stakeManager.registerClaim(sigData, *args)


def test_registerClaim_rev_sig(cf, stakedMin):
    _, st_amount = stakedMin
    args = (JUNK_HEX, st_amount, cf.DENICE, getChainTime() + CLAIM_DELAY + 5)
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[3] += 1

    with reverts(REV_MSG_SIG):
        cf.stakeManager.registerClaim(sigData, *args)


@given(
    st_sender=strategy("address"),
)
def test_registerClaim_rev_suspended(cf, stakedMin, st_sender):
    _, st_amount = stakedMin

    cf.stakeManager.suspend({"from": cf.GOVERNOR})

    with reverts(REV_MSG_GOV_SUSPENDED):
        args = (JUNK_HEX, st_amount, cf.DENICE, getChainTime() + CLAIM_DELAY)
        signed_call_cf(cf, cf.stakeManager.registerClaim, *args, sender=st_sender)
