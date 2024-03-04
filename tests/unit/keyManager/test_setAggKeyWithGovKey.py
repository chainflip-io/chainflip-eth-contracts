from consts import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy
from shared_tests import *
import time


def test_setAggKeyWithGovKey(cf):
    setAggKeyWithGovKey_test(cf)


def test_setAggKeyWithGovKey_delay_success(cf):
    chain.sleep(AGG_KEY_TIMEOUT)
    setAggKeyWithGovKey_test(cf)


def test_setAggKeyWithGovKey_rev_governor(cf):
    chain.sleep(AGG_KEY_TIMEOUT)
    with reverts(REV_MSG_KEYMANAGER_GOVERNOR):
        cf.keyManager.setAggKeyWithGovKey(
            cf.keyManager.getAggregateKey(), {"from": cf.ALICE}
        )


def test_setAggKeyWithGovKey_rev_nz(cf):
    chain.sleep(AGG_KEY_TIMEOUT)
    with reverts(REV_MSG_NZ_PUBKEYX):
        cf.keyManager.setAggKeyWithGovKey(NULL_KEY, {"from": cf.GOVERNOR})


def test_setAggKeyWithGovKey_rev_invalid(cf):
    chain.sleep(AGG_KEY_TIMEOUT)
    with reverts(REV_MSG_PUB_KEY_X):
        cf.keyManager.setAggKeyWithGovKey(BAD_AGG_KEY, {"from": cf.GOVERNOR})
