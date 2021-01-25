from shared_tests import *


def test_constructor(cf):
    assert cf.stakeManager.getKeyManager() == cf.keyManager.address
    txTimeTest(cf.stakeManager.getLastClaimTime(), cf.stakeManager.tx)
    assert cf.stakeManager.getEmissionPerSec() == EMISSION_PER_SEC
    assert cf.stakeManager.getTotalStaked() == 0
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE