from consts import *
from shared_tests import *


# This also implicitly tests these getters too
def test_constructor(a, cf):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == cf.GOVERNOR
    assert cf.keyManager.canConsumeNonceSet() == True
    cf.whitelisted = [cf.vault, cf.stakeManager, cf.keyManager, cf.flip]
    for addr in cf.whitelisted + list(a):
        assert cf.keyManager.canConsumeNonce(addr) == (
            True if addr in cf.whitelisted else False
        )

    assert cf.keyManager.getNumberWhitelistedAddresses() == len(cf.whitelisted)


def test_constructor_AW(a, cfAW):
    assert cfAW.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cfAW.keyManager.getGovernanceKey() == cfAW.GOVERNOR
    assert cfAW.keyManager.canConsumeNonceSet() == True
    cfAW.whitelisted = [
        cfAW.vault,
        cfAW.keyManager,
        cfAW.stakeManager,
        cfAW.flip,
    ] + list(a)
    for addr in cfAW.whitelisted:
        assert cfAW.keyManager.canConsumeNonce(addr) == True

    assert cfAW.keyManager.getNumberWhitelistedAddresses() == len(cfAW.whitelisted)
