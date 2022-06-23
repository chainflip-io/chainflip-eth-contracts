from consts import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy
from utils import *
from shared_tests import *


def test_setGovKeyWithAggKey(cf):
    setGovKeyWithAggKey_test(cf)


def test_setGovKeyWithAggKey_rev(cf):
    with reverts(REV_MSG_NZ_ADDR):
        signed_call_cf(
            cf, cf.keyManager.setGovKeyWithAggKey, ZERO_ADDR, sender=cf.ALICE
        )
