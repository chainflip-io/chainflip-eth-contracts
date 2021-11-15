from consts import *
from shared_tests import *


# This also implicitly tests these getters too
def test_constructor(a, cf):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == GOV_SIGNER_1.getPubDataWith0x()
    txTimeTest(cf.keyManager.getLastValidateTime(), cf.keyManager.tx)
    assert cf.keyManager.canValidateSigSet() == True
    whitelisted = [cf.vault, cf.keyManager, cf.stakeManager]
    for addr in whitelisted + list(a):
        assert cf.keyManager.canValidateSig(addr) == (True if addr in whitelisted else False)