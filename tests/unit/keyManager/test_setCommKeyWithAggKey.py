from consts import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy
from utils import *
from shared_tests import *


def test_setCommKeyWithAggKey(cfDeploy):
    setCommKeyWithAggKey_test(cfDeploy)


def test_setCommKeyWithAggKey_rev(cfDeploy):
    with reverts(REV_MSG_NZ_ADDR):
        signed_call_aggSigner(
            cfDeploy,
            cfDeploy.keyManager.setCommKeyWithAggKey,
            ZERO_ADDR,
            sender=cfDeploy.ALICE,
        )
