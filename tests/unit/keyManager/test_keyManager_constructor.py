from consts import *
from shared_tests import *


# This also implicitly tests these getters too
def test_constructor(a, cf):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == cf.GOVERNOR
    assert cf.keyManager.canConsumeKeyNonceSet() == True
    for addr in cf.whitelisted + list(a):
        assert cf.keyManager.canConsumeKeyNonce(addr) == (
            True if addr in cf.whitelisted else False
        )

    assert cf.keyManager.getNumberWhitelistedAddresses() == len(cf.whitelisted)


def test_constructor_AW(a, cfAW):
    assert cfAW.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cfAW.keyManager.getGovernanceKey() == cfAW.GOVERNOR
    assert cfAW.keyManager.canConsumeKeyNonceSet() == True
    for addr in cfAW.whitelisted:
        assert cfAW.keyManager.canConsumeKeyNonce(addr) == True

    assert cfAW.keyManager.getNumberWhitelistedAddresses() == len(cfAW.whitelisted)
