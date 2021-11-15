from consts import *
from brownie import reverts
from shared_tests import *


def test_setGovKeyWithGovKey(cfAW):
    setGovKeyWithGovKey_test(cfAW)


def test_setGovKeyWithGovKey_rev_pubKeyX(cfAW):
    setKey_rev_pubKeyX_test(cfAW, cfAW.keyManager.setGovKeyWithGovKey, GOV_SIGNER_1)


def test_setGovKeyWithGovKey_rev_nonceTimesGAddr(cfAW):
    setKey_rev_nonceTimesGAddr_test(cfAW, cfAW.keyManager.setGovKeyWithGovKey, GOV_SIGNER_1)


def test_setGovKeyWithGovKey_rev_msgHash(cfAW):
    setKey_rev_msgHash_test(cfAW, cfAW.keyManager.setGovKeyWithGovKey, GOV_SIGNER_1)


def test_setGovKeyWithGovKey_rev_sig(cfAW):
    setKey_rev_sig_test(cfAW, cfAW.keyManager.setGovKeyWithGovKey, GOV_SIGNER_1)