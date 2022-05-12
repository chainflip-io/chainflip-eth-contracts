from consts import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy
from utils import *
from shared_tests import *


def test_setCommKeyWithAggKey(cf):
    setCommKeyWithAggKey_test(cf)


def test_setCommKeyWithAggKey_rev(cf):
    callDataNoSig = cf.keyManager.setCommKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), ZERO_ADDR
    )

    with reverts(REV_MSG_NZ_ADDR):
        cf.keyManager.setCommKeyWithAggKey(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            ZERO_ADDR,
            {"from": cf.ALICE},
        )
