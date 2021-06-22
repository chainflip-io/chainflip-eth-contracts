from consts import *
from shared_tests import *
from brownie import reverts, web3, chain
from brownie.test import given, strategy


@given(
    amount=strategy('uint', exclude=0),
    staker=strategy('address'),
    # 5s because without a buffer time, the time that the tx actually executes may have changed
    # and make the test fail even though nothing is wrong
    expiryTimeDiff=strategy('uint', min_value=5, max_value=365*DAY)
)
def test_registerClaim_amount_rand(cf, stakedMin, amount, staker, expiryTimeDiff):
    args = (JUNK_HEX, amount, staker, chain.time() + CLAIM_DELAY + expiryTimeDiff)
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(agg_null_sig(), *args)
    if amount == 0:
        with reverts(REV_MSG_NZ_UINT):
            cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args)
    else:
        registerClaimTest(cf, cf.stakeManager.tx, MIN_STAKE, JUNK_HEX, EMISSION_PER_BLOCK, MIN_STAKE, amount, staker, chain.time() + (2 * CLAIM_DELAY))


# Specific amounts that should/shouldn't work


def test_registerClaim_min_expiryTime(cf, stakedMin):
    registerClaimTest(cf, cf.stakeManager.tx, MIN_STAKE, JUNK_HEX, EMISSION_PER_BLOCK, MIN_STAKE, MIN_STAKE, cf.DENICE, chain.time()+CLAIM_DELAY+5)


def test_registerClaim_rev_just_under_min_expiryTime(cf, stakedMin):
    _, amount = stakedMin
    args = (JUNK_HEX, amount, cf.DENICE, chain.time() + CLAIM_DELAY - 5)

    callDataNoSig = cf.stakeManager.registerClaim.encode_input(agg_null_sig(), *args)
    with reverts(REV_MSG_EXPIRY_TOO_SOON):
        cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args)


def test_registerClaim_claim_expired(cf, stakedMin):
    _, amount = stakedMin
    args = (JUNK_HEX, amount, cf.DENICE, chain.time() + CLAIM_DELAY + 5)
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(agg_null_sig(), *args)
    cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args)
    
    chain.sleep(CLAIM_DELAY + 10)
    registerClaimTest(cf, cf.stakeManager.tx, MIN_STAKE, JUNK_HEX, EMISSION_PER_BLOCK, MIN_STAKE, MIN_STAKE, cf.DENICE, chain.time()+(2*CLAIM_DELAY))


def test_registerClaim_rev_claim_not_expired(cf, stakedMin):
    _, amount = stakedMin
    args = (JUNK_HEX, amount, cf.DENICE, chain.time() + CLAIM_DELAY + 5)
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(agg_null_sig(), *args)
    cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args)

    callDataNoSig = cf.stakeManager.registerClaim.encode_input(agg_null_sig(), *args)
    with reverts(REV_MSG_CLAIM_EXISTS):
        cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args)


def test_registerClaim_rev_nodeID(cf, stakedMin):
    _, amount = stakedMin
    receiver = cf.DENICE
    args = (0, amount, receiver, chain.time() + CLAIM_DELAY + 5)

    callDataNoSig = cf.stakeManager.registerClaim.encode_input(agg_null_sig(), *args)
    with reverts(REV_MSG_NZ_BYTES32):
        cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args)


def test_registerClaim_rev_staker(cf, stakedMin):
    _, amount = stakedMin
    args = (JUNK_HEX, amount, ZERO_ADDR, chain.time() + CLAIM_DELAY + 5)

    callDataNoSig = cf.stakeManager.registerClaim.encode_input(agg_null_sig(), *args)
    with reverts(REV_MSG_NZ_ADDR):
        cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args)


def test_registerClaim_rev_msgHash(cf, stakedMin):
    _, amount = stakedMin
    receiver = cf.DENICE
    args = (JUNK_HEX, amount, cf.DENICE, chain.time() + CLAIM_DELAY + 5)
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(agg_null_sig(), *args)
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[0] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.stakeManager.registerClaim(sigData, *args)


def test_registerClaim_rev_sig(cf, stakedMin):
    _, amount = stakedMin
    receiver = cf.DENICE
    args = (JUNK_HEX, amount, cf.DENICE, chain.time() + CLAIM_DELAY + 5)
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(agg_null_sig(), *args)
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[1] += 1

    with reverts(REV_MSG_SIG):
        cf.stakeManager.registerClaim(sigData, *args)


# Can't use the normal StakeManager to test this since there's obviously
# intentionally no way to get FLIP out of the contract without calling `registerClaim`,
# so we have to use StakeManagerVulnerable which inherits StakeManager and
# has `testSendFLIP` in it to simulate some kind of hack
@given(amount=strategy('uint256', min_value=1, max_value=MIN_STAKE+1))
def test_registerClaim_rev_noFish(cf, vulnerableR3ktStakeMan, amount):
    smVuln, _ = vulnerableR3ktStakeMan
    args = (JUNK_HEX, amount, cf.DENICE, chain.time() + CLAIM_DELAY + 5)

    callDataNoSig = smVuln.registerClaim.encode_input(agg_null_sig(), *args)
    with reverts(REV_MSG_NO_FISH):
        smVuln.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args)