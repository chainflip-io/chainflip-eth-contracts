from consts import *
from brownie import reverts
from brownie.test import given, strategy


def test_govAction_rev(cf):
    with reverts(REV_MSG_KEYMANAGER_GOVERNOR):
        cf.keyManager.govAction(JUNK_HEX, {"from": cf.ALICE})


@given(st_message=strategy("bytes32"))
def test_govAction(cf, st_message):
    tx = cf.keyManager.govAction(st_message, {"from": cf.GOVERNOR})
    assert tx.events["GovernanceAction"]["message"] == "0x" + cleanHexStr(st_message)
