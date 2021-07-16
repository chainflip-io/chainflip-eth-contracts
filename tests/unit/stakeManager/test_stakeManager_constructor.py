from shared_tests import *


def test_constructor(cf, web3):
    assert cf.stakeManager.getKeyManager() == cf.keyManager.address
    assert cf.stakeManager.getLastSupplyUpdateBlockNumber() == 0
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE
    assert cf.flip.totalSupply() == INIT_SUPPLY
    assert cf.flip.balanceOf(cf.stakeManager) == 0