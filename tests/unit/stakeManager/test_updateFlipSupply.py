from consts import *
from brownie.test import given, strategy
from brownie import reverts, chain

def test_updateFlipSupply(cf):

    cf.stakeManager.stake(JUNK_HEX, MIN_STAKE, NON_ZERO_ADDR, {'from': cf.ALICE})

    assert cf.flip.balanceOf(cf.stakeManager) == MIN_STAKE
    assert cf.stakeManager.getLastSupplyUpdateBlockNumber() == 0

    stateChainBlockNumber = 1

    callDataNoSig = cf.stakeManager.updateFlipSupply.encode_input(agg_null_sig(), NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber)
    tx = cf.stakeManager.updateFlipSupply(AGG_SIGNER_1.getSigData(callDataNoSig), NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber, {"from": cf.ALICE})

    # Balance should be MIN_STAKE plus the minted delta
    assert cf.flip.balanceOf(cf.stakeManager) == NEW_TOTAL_SUPPLY_MINT - INIT_SUPPLY + MIN_STAKE
    assert cf.stakeManager.getLastSupplyUpdateBlockNumber() == stateChainBlockNumber
    assert tx.events["FlipSupplyUpdated"][0].values() == [INIT_SUPPLY, NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber]

    stateChainBlockNumber = 2

    callDataNoSig = cf.stakeManager.updateFlipSupply.encode_input(agg_null_sig(), INIT_SUPPLY, stateChainBlockNumber)
    tx2 = cf.stakeManager.updateFlipSupply(AGG_SIGNER_1.getSigData(callDataNoSig), INIT_SUPPLY, stateChainBlockNumber, {"from": cf.ALICE})

    # Balance should be MIN_STAKE as we've just burned all the FLIP we minted
    assert cf.flip.balanceOf(cf.stakeManager) == MIN_STAKE
    assert cf.stakeManager.getLastSupplyUpdateBlockNumber() == stateChainBlockNumber
    assert tx2.events["FlipSupplyUpdated"][0].values() == [NEW_TOTAL_SUPPLY_MINT, INIT_SUPPLY, stateChainBlockNumber]

    # Should not let us update the flip supply with an old block number
    stateChainBlockNumber = 1
    callDataNoSig = cf.stakeManager.updateFlipSupply.encode_input(agg_null_sig(), INIT_SUPPLY, stateChainBlockNumber)
    with reverts(REV_MSG_OLD_FLIP_SUPPLY_UPDATE):
        cf.stakeManager.updateFlipSupply(AGG_SIGNER_1.getSigData(callDataNoSig), INIT_SUPPLY, stateChainBlockNumber, {"from": cf.ALICE})
