from consts import *
from shared_tests import *


def test_rev_cfReceive_gas(
    cf,
    cfReceiverGriefer,
):
    cf.ALICE.transfer(cf.vault.address, TEST_AMNT * 10)
    tx = cfReceiverGriefer.cfReceive(0, 0, 0, NON_ZERO_ADDR, 0, {"from": cf.vault})
    assert tx.gas_used > 9 * 10**6
    assert "ReceivedxSwapAndCall" in tx.events

    tx = cfReceiverGriefer.cfReceivexCall(0, 0, 0, {"from": cf.vault})
    assert tx.gas_used > 9 * 10**6
    assert "ReceivedxCall" in tx.events
