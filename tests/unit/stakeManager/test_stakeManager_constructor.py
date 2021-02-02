from shared_tests import *


def test_constructor(a, cf, web3):
    assert cf.stakeManager.getKeyManager() == cf.keyManager.address
    assert cf.stakeManager.getLastMintBlockNum() == cf.stakeManager.tx.block_number
    assert cf.stakeManager.getEmissionPerBlock() == EMISSION_PER_BLOCK
    assert cf.stakeManager.getTotalStakeInFuture(0) == getInflation(cf.stakeManager.tx.block_number, web3.eth.blockNumber, EMISSION_PER_BLOCK)
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE
    assert cf.flip.totalSupply() == INITIAL_SUPPLY
    assert cf.flip.balanceOf(cf.stakeManager) == 0