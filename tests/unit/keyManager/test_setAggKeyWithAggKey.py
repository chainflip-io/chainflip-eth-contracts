from consts import *
from brownie import reverts
from shared_tests import *


def test_setAggKeyWithAggKey(cfAW):
    setAggKeyWithAggKey_test(cfAW)


def test_setAggKeyWithAggKey_rev_newPubKeyX(cf):
    setKey_rev_newPubKeyX_test(cf)


def test_setAggKeyWithAggKey_rev_pubKeyX(cfAW):
    newKey = AGG_SIGNER_2.getPubData()
    newKey[0] = 0
    with reverts(REV_MSG_NZ_PUBKEYX):
        signed_call_cf(cfAW, cfAW.keyManager.setAggKeyWithAggKey, newKey)


def test_setAggKeyWithAggKey_rev_nonceTimesGAddr(cfAW):
    newKey = AGG_SIGNER_2.getPubData()
    nullSig = agg_null_sig(cfAW.keyManager.address, chain.id)
    callDataNoSig = cfAW.keyManager.setAggKeyWithAggKey.encode_input(nullSig, newKey)
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cfAW.keyManager.address)
    sigData[3] = ZERO_ADDR
    with reverts(REV_MSG_INPUTS_0):
        cfAW.keyManager.setAggKeyWithAggKey(sigData, newKey)


def test_setAggKeyWithAggKey_rev_msgHash(cfAW):
    nullSig = agg_null_sig(cfAW.keyManager.address, chain.id)
    callDataNoSig = cfAW.keyManager.setAggKeyWithAggKey.encode_input(
        nullSig, AGG_SIGNER_2.getPubData()
    )
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cfAW.keyManager.address)
    sigData[2] += 1
    with reverts(REV_MSG_MSGHASH):
        cfAW.keyManager.setAggKeyWithAggKey(sigData, AGG_SIGNER_2.getPubData())


def test_setAggKeyWithAggKey_rev_sig(cfAW):
    nullSig = agg_null_sig(cfAW.keyManager.address, chain.id)
    callDataNoSig = cfAW.keyManager.setAggKeyWithAggKey.encode_input(
        nullSig, AGG_SIGNER_2.getPubData()
    )
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cfAW.keyManager.address)
    sigData[3] += 1
    with reverts(REV_MSG_SIG):
        cfAW.keyManager.setAggKeyWithAggKey(sigData, AGG_SIGNER_2.getPubData())
