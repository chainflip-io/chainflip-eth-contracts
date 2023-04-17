from consts import *
from brownie import reverts
from shared_tests import *


def test_setAggKeyWithAggKey(cf):
    setAggKeyWithAggKey_test(cf)


def test_setAggKeyWithAggKey_rev_newPubKeyX(cf):
    setKey_rev_newPubKeyX_test(cf)


def test_setAggKeyWithAggKey_rev_pubKeyX(cf):
    newKey = AGG_SIGNER_2.getPubData()
    newKey[0] = 0
    with reverts(REV_MSG_NZ_PUBKEYX):
        signed_call_cf(cf, cf.keyManager.setAggKeyWithAggKey, newKey)


def test_setAggKeyWithAggKey_rev_nonceTimesGAddr(cf):
    newKey = AGG_SIGNER_2.getPubData()

    sigData = AGG_SIGNER_1.getSigData(
        cf.keyManager, cf.keyManager.setAggKeyWithAggKey, newKey
    )
    sigData[2] = ZERO_ADDR

    with reverts(REV_MSG_INPUTS_0):
        cf.keyManager.setAggKeyWithAggKey(sigData, newKey, {"from": cf.ALICE})


def test_setAggKeyWithAggKey_rev_sig(cf):
    newKey = AGG_SIGNER_2.getPubData()

    sigData = AGG_SIGNER_1.getSigData(
        cf.keyManager, cf.keyManager.setAggKeyWithAggKey, newKey
    )

    sigdata_modif = sigData[:]
    sigdata_modif[0] += 1

    with reverts(REV_MSG_SIG):
        cf.keyManager.setAggKeyWithAggKey(sigdata_modif, newKey, {"from": cf.ALICE})

    sigdata_modif = sigData[:]
    sigdata_modif[1] += 1
    with reverts(REV_MSG_SIG):
        cf.keyManager.setAggKeyWithAggKey(sigdata_modif, newKey, {"from": cf.ALICE})

    sigdata_modif = sigData[:]
    sigdata_modif[2] = NON_ZERO_ADDR
    with reverts(REV_MSG_SIG):
        cf.keyManager.setAggKeyWithAggKey(sigdata_modif, newKey, {"from": cf.ALICE})
