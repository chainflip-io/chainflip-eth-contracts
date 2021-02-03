from consts import *
from shared_tests import *
from brownie import reverts


def test_isValidSig_setAggKeyWithAggKey_validate(cf):
    txTimeTest(cf.keyManager.getLastValidateTime(), cf.keyManager.tx)

    # Should validate successfully
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX)
    tx = cf.keyManager.isValidSig(cleanHexStr(sigData[0]), sigData, AGG_SIGNER_1.getPubData())

    txTimeTest(cf.keyManager.getLastValidateTime(), tx)

    # Should change key successfully
    setAggKeyWithAggKey_test(cf)

    # Should revert with old key
    # sigData = AGG_SIGNER_1.getSigData(JUNK_HEX)
    # with reverts(REV_MSG_SIG):
    #     cf.keyManager.isValidSig(cleanHexStr(sigData[0]), sigData, AGG_SIGNER_1.getPubData())

    # Should validate with new key