from consts import *
from brownie import reverts
from brownie.test import given, strategy


@given(newMinStake=strategy('uint256', exclude=0))
def test_setMinStake(cf, newMinStake):
    callDataNoSig = cf.stakeManager.setMinStake.encode_input(gov_null_sig(cf.keyManager.address, chain.id), newMinStake)
    tx = cf.stakeManager.setMinStake(GOV_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), newMinStake, cf.FR_ALICE)

    # Check things that should've changed
    assert cf.stakeManager.getMinimumStake() == newMinStake
    assert tx.events["MinStakeChanged"][0].values() == [MIN_STAKE, newMinStake]

    # Check things that shouldn't have changed
    assert cf.flip.balanceOf(cf.stakeManager) == STAKEMANAGER_INITIAL_BALANCE


def test_setMinStake_rev_amount(cf):
    callDataNoSig = cf.stakeManager.setMinStake.encode_input(gov_null_sig(cf.keyManager.address, chain.id), 0)
    with reverts(REV_MSG_NZ_UINT):
        cf.stakeManager.setMinStake(GOV_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), 0, cf.FR_ALICE)


def test_setMinStake_rev_msgHash(cf):
    callDataNoSig = cf.stakeManager.setMinStake.encode_input(gov_null_sig(cf.keyManager.address, chain.id), JUNK_HEX)
    sigData = GOV_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[0] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.stakeManager.setMinStake(sigData, JUNK_HEX)


def test_setMinStake_rev_sig(cf):
    callDataNoSig = cf.stakeManager.setMinStake.encode_input(gov_null_sig(cf.keyManager.address, chain.id), JUNK_HEX)
    sigData = GOV_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[1] += 1

    with reverts(REV_MSG_SIG):
        cf.stakeManager.setMinStake(sigData, JUNK_HEX)


def test_setMinStake_rev_aggKey(cf):
    callDataNoSig = cf.stakeManager.setMinStake.encode_input(agg_null_sig(cf.keyManager.address, chain.id), JUNK_HEX)
    with reverts(REV_MSG_SIG):
        cf.stakeManager.setMinStake(AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), JUNK_HEX)


# Can't use the normal StakeManager to test this since there's obviously
# intentionally no way to get FLIP out of the contract without calling `claim`,
# so we have to use StakeManagerVulnerable which inherits StakeManager and
# has `testSendFLIP` in it to simulate some kind of hack
@given(amount=strategy('uint256', min_value=1, max_value=MIN_STAKE+1))
def test_setMinStake_rev_noFish(cfAW, StakeManagerVulnerable, FLIP, web3, amount):
    smVuln = cfAW.DEPLOYER.deploy(StakeManagerVulnerable, cfAW.keyManager, MIN_STAKE, INIT_SUPPLY, NUM_GENESIS_VALIDATORS, GENESIS_STAKE)
    flipVuln = FLIP.at(smVuln.getFLIP())
    # Can't set _FLIP in the constructor because it's made in the constructor
    # of StakeManager and getFLIP is external
    smVuln.testSetFLIP(flipVuln)
    flipVuln.transfer(cfAW.ALICE, MAX_TEST_STAKE, {'from': cfAW.DEPLOYER})

    assert flipVuln.balanceOf(cfAW.CHARLIE) == 0
    # Need to stake 1st so that there's coins to hack out of it
    smVuln.stake(JUNK_HEX, MIN_STAKE, NON_ZERO_ADDR, {'from': cfAW.ALICE})
    # Somebody r3kts us somehow
    smVuln.testSendFLIP(cfAW.CHARLIE, amount)
    assert flipVuln.balanceOf(cfAW.CHARLIE) == amount

    # Ensure test doesn't fail because there aren't enough coins
    callDataNoSig = smVuln.setMinStake.encode_input(gov_null_sig(cf.keyManager.address, chain.id), JUNK_HEX)
    with reverts(REV_MSG_NO_FISH):
        smVuln.setMinStake(GOV_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), JUNK_HEX)
