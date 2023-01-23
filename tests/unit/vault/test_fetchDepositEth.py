from brownie import reverts, web3
from shared_tests import *
from consts import *
from utils import *


def test_fetchDepositNative(cf, DepositNative):
    fetchDepositNative(cf, cf.vault, DepositNative)


def test_fetchDepositNative_rev_swapID(cf):
    with reverts(REV_MSG_NZ_BYTES32):
        signed_call_cf(cf, cf.vault.fetchDepositNative, "")


def test_fetchDepositNative_rev_msgHash(cf):
    callDataNoSig = cf.vault.fetchDepositNative.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), JUNK_HEX_PAD
    )

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[2] += 1
    # Fetch the deposit
    with reverts(REV_MSG_MSGHASH):
        cf.vault.fetchDepositNative(sigData, JUNK_HEX_PAD)


def test_fetchDepositNative_rev_sig(cf):
    callDataNoSig = cf.vault.fetchDepositNative.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), JUNK_HEX_PAD
    )

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[3] += 1
    # Fetch the deposit
    with reverts(REV_MSG_SIG):
        cf.vault.fetchDepositNative(sigData, JUNK_HEX_PAD)
