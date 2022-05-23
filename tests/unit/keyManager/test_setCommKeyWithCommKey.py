from consts import *
from brownie import reverts
from shared_tests import *


def test_setCommKeyWithCommKey(cfDeploy):
    setCommKeyWithCommKey_test(cfDeploy)


def test_setCommKeyWithCommKey_rev_nzAddr(cfDeploy):
    with reverts(REV_MSG_NZ_ADDR):
        cfDeploy.keyManager.setCommKeyWithCommKey(
            ZERO_ADDR, {"from": cfDeploy.COMMUNITY_KEY}
        )


def test_setCommKeyWithCommKey_rev_comm(cfDeploy):
    with reverts(REV_MSG_KEYMANAGER_NOT_COMMUNITY):
        cfDeploy.keyManager.setCommKeyWithCommKey(ZERO_ADDR, {"from": cfDeploy.ALICE})
