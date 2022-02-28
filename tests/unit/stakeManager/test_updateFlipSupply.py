from consts import *
from brownie.test import given, strategy
from brownie import reverts, chain
from utils import *

def test_updateFlipSupply(cf):

    cf.stakeManager.stake(JUNK_HEX, MIN_STAKE, NON_ZERO_ADDR, {'from': cf.ALICE})

    assert cf.flip.balanceOf(cf.stakeManager) == MIN_STAKE + STAKEMANAGER_INITIAL_BALANCE
    assert cf.stakeManager.getLastSupplyUpdateBlockNumber() == 0

    stateChainBlockNumber = 1

    callDataNoSig = cf.stakeManager.updateFlipSupply.encode_input(agg_null_sig(cf.keyManager.address, chain.id), NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber)
    balanceBefore = cf.ALICE.balance()
    tx = cf.stakeManager.updateFlipSupply(AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber, cf.FR_ALICE)
    balanceAfter = cf.ALICE.balance()

    # Balance should be MIN_STAKE plus the minted delta
    assert cf.flip.balanceOf(cf.stakeManager) == NEW_TOTAL_SUPPLY_MINT - INIT_SUPPLY + MIN_STAKE + STAKEMANAGER_INITIAL_BALANCE
    assert cf.stakeManager.getLastSupplyUpdateBlockNumber() == stateChainBlockNumber
    assert tx.events["FlipSupplyUpdated"][0].values() == [INIT_SUPPLY, NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber]

    txRefundTest(balanceBefore, balanceAfter, tx)

    stateChainBlockNumber = 2

    callDataNoSig = cf.stakeManager.updateFlipSupply.encode_input(agg_null_sig(cf.keyManager.address, chain.id), INIT_SUPPLY, stateChainBlockNumber)
    balanceBefore2 = cf.ALICE.balance()
    tx2 = cf.stakeManager.updateFlipSupply(AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), INIT_SUPPLY, stateChainBlockNumber, cf.FR_ALICE)
    balanceAfter2 = cf.ALICE.balance()

    # Balance should be MIN_STAKE as we've just burned all the FLIP we minted
    assert cf.flip.balanceOf(cf.stakeManager) == MIN_STAKE + STAKEMANAGER_INITIAL_BALANCE
    assert cf.stakeManager.getLastSupplyUpdateBlockNumber() == stateChainBlockNumber
    assert tx2.events["FlipSupplyUpdated"][0].values() == [NEW_TOTAL_SUPPLY_MINT, INIT_SUPPLY, stateChainBlockNumber]

    txRefundTest(balanceBefore2, balanceAfter2, tx2)

    # Should not let us update the flip supply with an old block number
    stateChainBlockNumber = 1
    callDataNoSig = cf.stakeManager.updateFlipSupply.encode_input(agg_null_sig(cf.keyManager.address, chain.id), INIT_SUPPLY, stateChainBlockNumber)
    with reverts(REV_MSG_OLD_FLIP_SUPPLY_UPDATE):
        cf.stakeManager.updateFlipSupply(AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), INIT_SUPPLY, stateChainBlockNumber, cf.FR_ALICE)
