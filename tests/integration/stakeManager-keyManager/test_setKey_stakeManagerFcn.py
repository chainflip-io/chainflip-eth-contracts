from consts import *
from shared_tests import *
from brownie import reverts, web3


def test_setAggKeyWithAggKey_setEmissionPerBlock(cf):
    # Change agg keys
    setGovKeyWithGovKey_test(cf)

    newEmissionPerBlock = int(EMISSION_PER_BLOCK * 1.5)
    callDataNoSig = cf.stakeManager.setEmissionPerBlock.encode_input(gov_null_sig(), newEmissionPerBlock)
    
    # Changing emission with old key should revert
    with reverts(REV_MSG_SIG):
        cf.stakeManager.setEmissionPerBlock(GOV_SIGNER_1.getSigData(callDataNoSig), newEmissionPerBlock, {"from": cf.ALICE})

    # Change emission with new key
    callDataNoSig = cf.stakeManager.setEmissionPerBlock.encode_input(gov_null_sig(), newEmissionPerBlock)
    tx = cf.stakeManager.setEmissionPerBlock(GOV_SIGNER_2.getSigData(callDataNoSig), newEmissionPerBlock, {"from": cf.ALICE})
    
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


def test_setAggKeyWithAggKey_setMinStake(cf):
    # Change agg keys
    setGovKeyWithGovKey_test(cf)

    newMinStake = int(MIN_STAKE * 1.5)
    callDataNoSig = cf.stakeManager.setMinStake.encode_input(gov_null_sig(), newMinStake)
    
    # Changing emission with old key should revert
    with reverts(REV_MSG_SIG):
        cf.stakeManager.setMinStake(GOV_SIGNER_1.getSigData(callDataNoSig), newMinStake, {"from": cf.ALICE})

    # Change minStake with new key
    callDataNoSig = cf.stakeManager.setMinStake.encode_input(gov_null_sig(), newMinStake)
    tx = cf.stakeManager.setMinStake(GOV_SIGNER_2.getSigData(callDataNoSig), newMinStake, {"from": cf.ALICE})

    # Check things that should've changed
    assert cf.stakeManager.getMinimumStake() == newMinStake
    assert tx.events["MinStakeChanged"][0].values() == [MIN_STAKE, newMinStake]
    # Check things that shouldn't have changed
    inflation = getInflation(cf.stakeManager.tx.block_number, tx.block_number, EMISSION_PER_BLOCK)
    assert cf.flip.balanceOf(cf.stakeManager) == 0
    assert cf.stakeManager.getInflationInFuture(0) == inflation
    assert cf.stakeManager.getTotalStakeInFuture(0) == inflation
    assert cf.stakeManager.getEmissionPerBlock() == EMISSION_PER_BLOCK
    assert cf.stakeManager.getLastMintBlockNum() == cf.stakeManager.tx.block_number