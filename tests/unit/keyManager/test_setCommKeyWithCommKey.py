from consts import *
from brownie import reverts
from shared_tests import *


def test_setCommKeyWithCommKey(cf):
    setCommKeyWithCommKey_test(cf)


def test_setCommKeyWithCommKey_rev_nzAddr(cf):
    with reverts(REV_MSG_NZ_ADDR):
        cf.keyManager.setCommKeyWithCommKey(ZERO_ADDR, {"from": cf.COMMUNITY_KEY})


def test_setCommKeyWithCommKey_rev_comm(cf):
    with reverts(REV_MSG_KEYMANAGER_NOT_COMMUNITY):
        cf.keyManager.setCommKeyWithCommKey(ZERO_ADDR, {"from": cf.ALICE})
