from consts import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy
from shared_tests import *
import time


def test_setAggKeyWithGovKey(cf):
    chain.sleep(AGG_KEY_TIMEOUT)
    setAggKeyWithGovKey_test(cf)


def test_setAggKeyWithGovKey_rev_pubKeyX(cf):
    chain.sleep(AGG_KEY_TIMEOUT)
    setKey_rev_pubKeyX_test(cf, cf.keyManager.setAggKeyWithGovKey, GOV_SIGNER_1)


def test_setAggKeyWithGovKey_rev_nonceTimesGAddr(cf):
    chain.sleep(AGG_KEY_TIMEOUT)
    setKey_rev_nonceTimesGAddr_test(cf, cf.keyManager.setAggKeyWithGovKey, GOV_SIGNER_1)


def test_setAggKeyWithGovKey_rev_msgHash(cf):
    chain.sleep(AGG_KEY_TIMEOUT)
    setKey_rev_msgHash_test(cf, cf.keyManager.setAggKeyWithGovKey, GOV_SIGNER_1)


def test_setAggKeyWithGovKey_rev_sig(cf):
    chain.sleep(AGG_KEY_TIMEOUT)
    setKey_rev_sig_test(cf, cf.keyManager.setAggKeyWithGovKey, GOV_SIGNER_1)


@given(delay=strategy('uint256', max_value=AGG_KEY_TIMEOUT-1))
def test_setAggKeyWithGovKey_rev_delay(cf, delay):
    chain.sleep(delay)
    callDataNoSig = cf.keyManager.setAggKeyWithGovKey.encode_input(gov_null_sig(cf.keyManager.address, chain.id), AGG_SIGNER_2.getPubData())
    with reverts(REV_MSG_DELAY):
        cf.keyManager.setAggKeyWithGovKey(GOV_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), AGG_SIGNER_2.getPubData())