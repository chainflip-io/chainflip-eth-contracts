from consts import *
from brownie import reverts
from brownie.test import given, strategy


@given(newEmissionPerBlock=strategy('uint256', exclude=0))
def test_setEmissionPerBlock(cf, newEmissionPerBlock):
    callDataNoSig = cf.stakeManager.setEmissionPerBlock.encode_input(NULL_SIG_DATA, newEmissionPerBlock)
    tx = cf.stakeManager.setEmissionPerBlock(GOV_SIGNER_1.getSigData(callDataNoSig), newEmissionPerBlock, {"from": cf.ALICE})
    
    # Check things that should've changed
    inflation = getInflation(cf.stakeManager.tx.block_number, tx.block_number, EMISSION_PER_BLOCK)
    assert cf.flip.balanceOf(cf.stakeManager) == inflation
    assert cf.stakeManager.getInflationInFuture(0) == 0
    assert cf.stakeManager.getTotalStakeInFuture(0) == inflation
    assert cf.stakeManager.getEmissionPerBlock() == newEmissionPerBlock
    assert cf.stakeManager.getLastMintBlockNum() == tx.block_number
    assert tx.events["EmissionChanged"][0].values() == [EMISSION_PER_BLOCK, newEmissionPerBlock]
    # Check things that shouldn't have changed
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE


def test_setEmissionPerBlock_rev_amount(cf):
    callDataNoSig = cf.stakeManager.setEmissionPerBlock.encode_input(NULL_SIG_DATA, 0)
    with reverts(REV_MSG_NZ_UINT):
        cf.stakeManager.setEmissionPerBlock(GOV_SIGNER_1.getSigData(callDataNoSig), 0, {"from": cf.ALICE})


def test_setEmissionPerBlock_rev_msgHash(cf):
    callDataNoSig = cf.stakeManager.setEmissionPerBlock.encode_input(NULL_SIG_DATA, JUNK_INT)
    sigData = GOV_SIGNER_1.getSigData(callDataNoSig)
    sigData[0] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.stakeManager.setEmissionPerBlock(sigData, JUNK_INT)


def test_setEmissionPerBlock_rev_sig(cf):
    callDataNoSig = cf.stakeManager.setEmissionPerBlock.encode_input(NULL_SIG_DATA, JUNK_INT)
    sigData = GOV_SIGNER_1.getSigData(callDataNoSig)
    sigData[1] += 1

    with reverts(REV_MSG_SIG):
        cf.stakeManager.setEmissionPerBlock(sigData, JUNK_INT)


def test_setEmissionPerBlock_rev_aggKey(cf):
    callDataNoSig = cf.stakeManager.setEmissionPerBlock.encode_input(NULL_SIG_DATA, JUNK_INT)
    with reverts(REV_MSG_SIG):
        cf.stakeManager.setEmissionPerBlock(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_INT)


# Can't use the normal StakeManager to test this since there's obviously
# intentionally no way to get FLIP out of the contract without calling `claim`,
# so we have to use StakeManagerVulnerable which inherits StakeManager and
# has `testSendFLIP` in it to simulate some kind of hack
@given(amount=strategy('uint256', min_value=1, max_value=MIN_STAKE+1))
def test_setEmissionPerBlock_rev_noFish(cf, vulnerableR3ktStakeMan, FLIP, web3, amount):
    smVuln, flipVuln = vulnerableR3ktStakeMan

    # Ensure test doesn't fail because there aren't enough coins
    callDataNoSig = smVuln.setEmissionPerBlock.encode_input(NULL_SIG_DATA, JUNK_INT)
    with reverts(REV_MSG_NO_FISH):
        smVuln.setEmissionPerBlock(GOV_SIGNER_1.getSigData(callDataNoSig), JUNK_INT)
