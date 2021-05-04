from consts import *
from brownie import reverts
from brownie.test import given, strategy


@given(newMinStake=strategy('uint256', exclude=0))
def test_setMinStake(cf, newMinStake):
    callDataNoSig = cf.stakeManager.setMinStake.encode_input(NULL_SIG_DATA, newMinStake)
    tx = cf.stakeManager.setMinStake(GOV_SIGNER_1.getSigData(callDataNoSig), newMinStake, {"from": cf.ALICE})
    
    # Check things that should've changed
    assert cf.stakeManager.getMinimumStake() == newMinStake
    assert tx.events["MinStakeChanged"][0].values() == [MIN_STAKE, newMinStake]
    # Check things that shouldn't have changed
    inflation = getInflation(cf.stakeManager.tx.blockNumber, tx.blockNumber, EMISSION_PER_BLOCK)
    assert cf.flip.balanceOf(cf.stakeManager) == 0
    assert cf.stakeManager.getInflationInFuture(0) == inflation
    assert cf.stakeManager.getTotalStakeInFuture(0) == inflation
    assert cf.stakeManager.getEmissionPerBlock() == EMISSION_PER_BLOCK
    assert cf.stakeManager.getLastMintBlockNum() == cf.stakeManager.tx.blockNumber


def test_setMinStake_rev_amount(cf):
    callDataNoSig = cf.stakeManager.setMinStake.encode_input(NULL_SIG_DATA, 0)
    with reverts(REV_MSG_NZ_UINT):
        cf.stakeManager.setMinStake(GOV_SIGNER_1.getSigData(callDataNoSig), 0, {"from": cf.ALICE})


def test_setMinStake_rev_msgHash(cf):
    callDataNoSig = cf.stakeManager.setMinStake.encode_input(NULL_SIG_DATA, JUNK_INT)
    sigData = GOV_SIGNER_1.getSigData(callDataNoSig)
    sigData[0] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.stakeManager.setMinStake(sigData, JUNK_INT)


def test_setMinStake_rev_sig(cf):
    callDataNoSig = cf.stakeManager.setMinStake.encode_input(NULL_SIG_DATA, JUNK_INT)
    sigData = GOV_SIGNER_1.getSigData(callDataNoSig)
    sigData[1] += 1

    with reverts(REV_MSG_SIG):
        cf.stakeManager.setMinStake(sigData, JUNK_INT)


def test_setMinStake_rev_aggKey(cf):
    callDataNoSig = cf.stakeManager.setMinStake.encode_input(NULL_SIG_DATA, JUNK_INT)
    with reverts(REV_MSG_SIG):
        cf.stakeManager.setMinStake(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_INT)


# Can't use the normal StakeManager to test this since there's obviously
# intentionally no way to get FLIP out of the contract without calling `claim`,
# so we have to use StakeManagerVulnerable which inherits StakeManager and
# has `testSendFLIP` in it to simulate some kind of hack
@given(amount=strategy('uint256', min_value=1, max_value=MIN_STAKE+1))
def test_setMinStake_rev_noFish(cf, StakeManagerVulnerable, FLIP, web3, amount):
    smVuln = cf.DEPLOYER.deploy(StakeManagerVulnerable, cf.keyManager, EMISSION_PER_BLOCK, MIN_STAKE, INIT_SUPPLY)
    flipVuln = FLIP.at(smVuln.getFLIPAddress())
    # Can't set _FLIP in the constructor because it's made in the constructor
    # of StakeManager and getFLIPAddress is external
    smVuln.testSetFLIP(flipVuln)
    flipVuln.transfer(cf.ALICE, MAX_TEST_STAKE, {'from': cf.DEPLOYER})
    flipVuln.approve(smVuln, MAX_TEST_STAKE, {'from': cf.ALICE})
    
    assert flipVuln.balanceOf(cf.CHARLIE) == 0
    # Need to stake 1st so that there's coins to hack out of it
    smVuln.stake(JUNK_INT, MIN_STAKE, {'from': cf.ALICE})
    # Somebody r3kts us somehow
    smVuln.testSendFLIP(cf.CHARLIE, amount)
    assert flipVuln.balanceOf(cf.CHARLIE) == amount

    # Ensure test doesn't fail because there aren't enough coins
    callDataNoSig = smVuln.setMinStake.encode_input(NULL_SIG_DATA, JUNK_INT)
    with reverts(REV_MSG_NO_FISH):
        smVuln.setMinStake(GOV_SIGNER_1.getSigData(callDataNoSig), JUNK_INT)
