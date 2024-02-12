from consts import *
from shared_tests import *


# This also implicitly tests these getters too
def test_constructor(a, cf):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == cf.GOVERNOR
    assert cf.keyManager.getLastValidateTime() == 0
