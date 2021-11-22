from consts import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy
from shared_tests import *
import time


def test_setAggKeyWithGovKey(cfAW):
    chain.sleep(AGG_KEY_TIMEOUT)
    setAggKeyWithGovKey_test(cfAW)

# def test_setAggKeyWithGovKey_rev_pubKeyX(cfAW):
#     chain.sleep(AGG_KEY_TIMEOUT)
#     setKey_rev_pubKeyX_test(cfAW, cfAW.keyManager.setAggKeyWithGovKey, GOV_SIGNER_1)

# def test_setAggKeyWithGovKey_rev_nonceTimesGAddr(cfAW):
#     chain.sleep(AGG_KEY_TIMEOUT)
#     setKey_rev_nonceTimesGAddr_test(cfAW, cfAW.keyManager.setAggKeyWithGovKey, GOV_SIGNER_1)

# def test_setAggKeyWithGovKey_rev_msgHash(cfAW):
#     chain.sleep(AGG_KEY_TIMEOUT)
#     setKey_rev_msgHash_test(cfAW, cfAW.keyManager.setAggKeyWithGovKey, GOV_SIGNER_1)


# def test_setAggKeyWithGovKey_rev_sig(cfAW):
#     chain.sleep(AGG_KEY_TIMEOUT)
#     setKey_rev_sig_test(cfAW, cfAW.keyManager.setAggKeyWithGovKey, GOV_SIGNER_1)


# @given(delay=strategy('uint256', max_value=AGG_KEY_TIMEOUT-1))
# def test_setAggKeyWithGovKey_rev_delay(cfAW, delay):
#     chain.sleep(delay)
#     callDataNoSig = cfAW.keyManager.setAggKeyWithGovKey.encode_input(gov_null_sig(cfAW.keyManager.address, chain.id), AGG_SIGNER_2.getPubData())
#     with reverts(REV_MSG_DELAY):
#         cfAW.keyManager.setAggKeyWithGovKey(GOV_SIGNER_1.getSigData(callDataNoSig, cfAW.keyManager.address), AGG_SIGNER_2.getPubData())
