from consts import *
from shared_tests import *
from brownie import reverts, web3, chain
from brownie.test import given, strategy


@given(
    amount=strategy("uint", exclude=0),
    staker=strategy("address"),
    # 5s because without a buffer time, the time that the tx actually executes may have changed
    # and make the test fail even though nothing is wrong
    expiryTimeDiff=strategy("uint", min_value=5, max_value=365 * DAY),
)
def test_registerClaim_amount_rand(cf, stakedMin, amount, staker, expiryTimeDiff):
    args = (JUNK_HEX, amount, staker, getChainTime() + CLAIM_DELAY + expiryTimeDiff)
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    if amount == 0:
        with reverts(REV_MSG_NZ_UINT):
            cf.stakeManager.registerClaim(
                AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), *args
            )
    else:
        registerClaimTest(
            cf, JUNK_HEX, MIN_STAKE, amount, staker, getChainTime() + (2 * CLAIM_DELAY)
        )


# Specific amounts that should/shouldn't work


def test_registerClaim_min_expiryTime(cf, stakedMin):
    registerClaimTest(
        cf, JUNK_HEX, MIN_STAKE, MIN_STAKE, cf.DENICE, getChainTime() + CLAIM_DELAY + 5
    )


def test_registerClaim_rev_just_under_min_expiryTime(cf, stakedMin):
    _, amount = stakedMin
    args = (JUNK_HEX, amount, cf.DENICE, getChainTime() + CLAIM_DELAY - 5)

    callDataNoSig = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    with reverts(REV_MSG_EXPIRY_TOO_SOON):
        cf.stakeManager.registerClaim(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), *args
        )


def test_registerClaim_claim_expired(cf, stakedMin):
    _, amount = stakedMin
    args = (JUNK_HEX, amount, cf.DENICE, getChainTime() + CLAIM_DELAY + 5)
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    cf.stakeManager.registerClaim(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), *args
    )

    chain.sleep(CLAIM_DELAY + 10)
    registerClaimTest(
        cf,
        JUNK_HEX,
        MIN_STAKE,
        MIN_STAKE,
        cf.DENICE,
        getChainTime() + (2 * CLAIM_DELAY),
    )


def test_registerClaim_rev_claim_not_expired(cf, stakedMin):
    _, amount = stakedMin
    args = (JUNK_HEX, amount, cf.DENICE, getChainTime() + CLAIM_DELAY + 5)
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    cf.stakeManager.registerClaim(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), *args
    )

    callDataNoSig = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    with reverts(REV_MSG_CLAIM_EXISTS):
        cf.stakeManager.registerClaim(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), *args
        )


def test_registerClaim_rev_nodeID(cf, stakedMin):
    _, amount = stakedMin
    receiver = cf.DENICE
    args = (0, amount, receiver, getChainTime() + CLAIM_DELAY + 5)

    callDataNoSig = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    with reverts(REV_MSG_NZ_BYTES32):
        cf.stakeManager.registerClaim(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), *args
        )


def test_registerClaim_rev_staker(cf, stakedMin):
    _, amount = stakedMin
    args = (JUNK_HEX, amount, ZERO_ADDR, getChainTime() + CLAIM_DELAY + 5)

    callDataNoSig = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    with reverts(REV_MSG_NZ_ADDR):
        cf.stakeManager.registerClaim(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), *args
        )


def test_registerClaim_rev_msgHash(cf, stakedMin):
    _, amount = stakedMin
    receiver = cf.DENICE
    args = (JUNK_HEX, amount, cf.DENICE, getChainTime() + CLAIM_DELAY + 5)
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[2] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.stakeManager.registerClaim(sigData, *args)


def test_registerClaim_rev_sig(cf, stakedMin):
    _, amount = stakedMin
    receiver = cf.DENICE
    args = (JUNK_HEX, amount, cf.DENICE, getChainTime() + CLAIM_DELAY + 5)
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[3] += 1

    with reverts(REV_MSG_SIG):
        cf.stakeManager.registerClaim(sigData, *args)
