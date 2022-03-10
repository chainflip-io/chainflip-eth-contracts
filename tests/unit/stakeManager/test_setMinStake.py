from consts import *
from brownie import reverts
from brownie.test import given, strategy


@given(newMinStake=strategy("uint256", exclude=0))
def test_setMinStake(cf, newMinStake):
    tx = cf.stakeManager.setMinStake(newMinStake, {"from": cf.GOVERNOR})

    # Check things that should've changed
    assert cf.stakeManager.getMinimumStake() == newMinStake
    assert tx.events["MinStakeChanged"][0].values() == [MIN_STAKE, newMinStake]

    # Check things that shouldn't have changed
    assert cf.flip.balanceOf(cf.stakeManager) == STAKEMANAGER_INITIAL_BALANCE


def test_setMinStake_rev_amount(cf):
    with reverts(REV_MSG_NZ_UINT):
        cf.stakeManager.setMinStake(0, {"from": cf.GOVERNOR})


def test_setMinStake_rev_governor(cf):
    with reverts(REV_MSG_STAKEMAN_GOVERNOR):
        cf.stakeManager.setMinStake(1, {"from": cf.ALICE})


# Can't use the normal StakeManager to test this since there's obviously
# intentionally no way to get FLIP out of the contract without calling `claim`,
# so we have to use StakeManagerVulnerable which inherits StakeManager and
# has `testSendFLIP` in it to simulate some kind of hack
@given(amount=strategy("uint256", min_value=1, max_value=MIN_STAKE + 1))
def test_setMinStake_rev_noFish(cf, vulnerableR3ktStakeMan, FLIP, web3, amount):
    # smVuln = cfAW.DEPLOYER.deploy(StakeManagerVulnerable, cfAW.keyManager, MIN_STAKE, INIT_SUPPLY, NUM_GENESIS_VALIDATORS, GENESIS_STAKE)
    # flipVuln = FLIP.at(smVuln.getFLIP())
    # # Can't set _FLIP in the constructor because it's made in the constructor
    # # of StakeManager and getFLIP is external
    # smVuln.testSetFLIP(flipVuln)
    # flipVuln.transfer(cfAW.ALICE, MAX_TEST_STAKE, {'from': cfAW.DEPLOYER})

    # assert flipVuln.balanceOf(cfAW.CHARLIE) == 0
    # # Need to stake 1st so that there's coins to hack out of it
    # smVuln.stake(JUNK_HEX, MIN_STAKE, NON_ZERO_ADDR, {'from': cfAW.ALICE})
    # # Somebody r3kts us somehow
    # smVuln.testSendFLIP(cfAW.CHARLIE, amount)
    # assert flipVuln.balanceOf(cfAW.CHARLIE) == amount

    cf, smVuln, _ = vulnerableR3ktStakeMan

    # Ensure test doesn't fail because there aren't enough coins
    with reverts(REV_MSG_NO_FISH):
        smVuln.setMinStake(JUNK_HEX, {"from": cf.GOVERNOR})
