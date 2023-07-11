from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy


def test_rev_cfReceive_gas(
    cf,
    cfReceiverGriefer,
):
    cf.ALICE.transfer(cf.vault.address, TEST_AMNT * 10)
    cfReceiverGriefer.cfReceive(0, 0, 0, NON_ZERO_ADDR, 0, {"from": cf.vault})
