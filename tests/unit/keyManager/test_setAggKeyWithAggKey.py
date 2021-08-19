from consts import *
from brownie import reverts
from shared_tests import *


def test_setAggKeyWithAggKey(cf):
    setAggKeyWithAggKey_test(cf)


def test_setAggKeyWithAggKey_rev_pubKeyX(cf):
    setKey_rev_pubKeyX_test(cf, cf.keyManager.setAggKeyWithAggKey, AGG_SIGNER_1)


def test_setAggKeyWithAggKey_rev_nonceTimesGAddr(cf):
    setKey_rev_nonceTimesGAddr_test(cf, cf.keyManager.setAggKeyWithAggKey, AGG_SIGNER_1)


def test_setAggKeyWithAggKey_rev_msgHash(cf):
    setKey_rev_msgHash_test(cf, cf.keyManager.setAggKeyWithAggKey, AGG_SIGNER_1)


def test_setAggKeyWithAggKey_rev_sig(cf):
    setKey_rev_sig_test(cf, cf.keyManager.setAggKeyWithAggKey, AGG_SIGNER_1)