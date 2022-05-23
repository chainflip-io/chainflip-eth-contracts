from consts import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy
from utils import *
from shared_tests import *


def test_setCommKeyWithAggKey(cf):
    setCommKeyWithAggKey_test(cf)


def test_setCommKeyWithAggKey_rev(cf):
    with reverts(REV_MSG_NZ_ADDR):
        signed_call_aggSigner(
            cf, cf.keyManager.setCommKeyWithAggKey, ZERO_ADDR, sender=cf.ALICE
        )
