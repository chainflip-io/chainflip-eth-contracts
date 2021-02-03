from consts import *
from brownie import reverts
from shared_tests import *


def test_setAggKeyWithGovKey(cf):
    setAggKeyWithGovKey_test(cf)


def test_setAggKeyWithGovKey_rev_pubKeyX(cf):
    setKey_rev_pubKeyX_test(cf, cf.keyManager.setAggKeyWithGovKey, GOV_SIGNER_1)


def test_setAggKeyWithGovKey_rev_nonceTimesGAddr(cf):
    setKey_rev_nonceTimesGAddr_test(cf, cf.keyManager.setAggKeyWithGovKey, GOV_SIGNER_1)


def test_setAggKeyWithGovKey_rev_msgHash(cf):
    setKey_rev_msgHash_test(cf, cf.keyManager.setAggKeyWithGovKey, GOV_SIGNER_1)


def test_setAggKeyWithGovKey_rev_sig(cf):
    setKey_rev_sig_test(cf, cf.keyManager.setAggKeyWithGovKey, GOV_SIGNER_1)