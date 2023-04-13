from consts import *
from brownie import reverts
from shared_tests import *


def test_setGovKeyWithGovKey(cf):
    setGovKeyWithGovKey_test(cf)


def test_setGovKeyWithGovKey_rev(cf):
    with reverts(REV_MSG_KEYMANAGER_GOVERNOR):
        cf.keyManager.setGovKeyWithGovKey(cf.ALICE, {"from": cf.ALICE})


def test_setGovKeyWithGovKey_rev_nz(cf):
    with reverts(REV_MSG_NZ_ADDR):
        cf.keyManager.setGovKeyWithGovKey(ZERO_ADDR, {"from": cf.GOVERNOR})
