from consts import *
from brownie import reverts
from brownie.test import given, strategy


def test_govAction_rev(cf):
    with reverts(REV_MSG_KEYMANAGER_GOVERNOR):
        cf.keyManager.govAction(JUNK_HEX, {"from": cf.ALICE})


@given(st_callHash=strategy("bytes32"))
def test_govAction(cf, st_callHash):
    tx = cf.keyManager.govAction(st_callHash, {"from": cf.GOVERNOR})
    assert tx.events["GovernanceAction"]["callHash"] == "0x" + cleanHexStr(st_callHash)
