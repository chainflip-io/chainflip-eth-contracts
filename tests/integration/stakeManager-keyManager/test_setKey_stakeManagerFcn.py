from consts import *
from shared_tests import *
from brownie import reverts, web3

def test_setAggKeyWithAggKey_updateFlipSupply(cf):
    # Change agg keys
    setAggKeyWithAggKey_test(cf)

    stateChainBlockNumber = 1

    callDataNoSig = cf.stakeManager.updateFlipSupply.encode_input(agg_null_sig(), NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber)

    # Changing emission with old key should revert
    with reverts(REV_MSG_SIG):
        cf.stakeManager.updateFlipSupply(AGG_SIGNER_1.getSigData(callDataNoSig), NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber, cf.FR_ALICE)

    # Change emission with new key
    callDataNoSig = cf.stakeManager.updateFlipSupply.encode_input(agg_null_sig(), NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber)
    tx = cf.stakeManager.updateFlipSupply(AGG_SIGNER_2.getSigData(callDataNoSig), NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber, cf.FR_ALICE)

    # Check things that should've changed
    assert cf.flip.totalSupply() == NEW_TOTAL_SUPPLY_MINT
    assert cf.flip.balanceOf(cf.stakeManager) == NEW_TOTAL_SUPPLY_MINT - INIT_SUPPLY + STAKEMANAGER_INITIAL_BALANCE
    assert cf.stakeManager.getLastSupplyUpdateBlockNumber() == stateChainBlockNumber
    assert tx.events["FlipSupplyUpdated"][0].values() == [INIT_SUPPLY, NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber]

    # Check things that shouldn't have changed
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE


def test_setGovKeyWithGovKey_setMinStake(cf):
    # Change agg keys
    setGovKeyWithGovKey_test(cf)

    newMinStake = int(MIN_STAKE * 1.5)
    callDataNoSig = cf.stakeManager.setMinStake.encode_input(gov_null_sig(), newMinStake)

    # Changing emission with old key should revert
    with reverts(REV_MSG_SIG):
        cf.stakeManager.setMinStake(GOV_SIGNER_1.getSigData(callDataNoSig), newMinStake, cf.FR_ALICE)

    # Change minStake with new key
    callDataNoSig = cf.stakeManager.setMinStake.encode_input(gov_null_sig(), newMinStake)
    tx = cf.stakeManager.setMinStake(GOV_SIGNER_2.getSigData(callDataNoSig), newMinStake, cf.FR_ALICE)

    # Check things that should've changed
    assert cf.stakeManager.getMinimumStake() == newMinStake
    assert tx.events["MinStakeChanged"][0].values() == [MIN_STAKE, newMinStake]

    # Check things that shouldn't have changed
    assert cf.flip.balanceOf(cf.stakeManager) == STAKEMANAGER_INITIAL_BALANCE