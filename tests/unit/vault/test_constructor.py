from consts import *
from shared_tests import *


# This also implicitly tests these getters too
def test_constructor(vault):
    assert vault.getAggregateKeyData() == AGG_SIGNER_1.getPubDataWith0x()
    assert vault.getGovernanceKeyData() == GOV_SIGNER_1.getPubDataWith0x()
    txTimeTest(vault.getLastValidateTime(), vault.tx)
