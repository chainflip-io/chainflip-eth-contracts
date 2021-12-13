from consts import *
from shared_tests import *


# This also implicitly tests these getters too
def test_constructor(cf):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == GOV_SIGNER_1.getPubDataWith0x()
    txTimeTest(cf.keyManager.getLastValidateTime(), cf.keyManager.tx)

def test_validAggKey(cf, KeyManager):
    with reverts(REV_MSG_PUB_KEY_X):
        cf.ALICE.deploy(KeyManager, BAD_AGG_KEY, GOV_SIGNER_1.getPubDataWith0x())