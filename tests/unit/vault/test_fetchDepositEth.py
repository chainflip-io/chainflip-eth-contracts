from brownie import reverts, web3
from shared_tests import *
from consts import *
from utils import *


def test_fetchDepositEth(cf, DepositEth):
    fetchDepositEth(cf, cf.vault, DepositEth)


def test_fetchDepositEth_rev_swapID(cf):
    with reverts(REV_MSG_NZ_BYTES32):
        signed_call_cf(cf, cf.vault.fetchDepositEth, "")


def test_fetchDepositEth_rev_msgHash(cf):
    callDataNoSig = cf.vault.fetchDepositEth.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), JUNK_HEX_PAD
    )

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[2] += 1
    # Fetch the deposit
    with reverts(REV_MSG_MSGHASH):
        cf.vault.fetchDepositEth(sigData, JUNK_HEX_PAD)


def test_fetchDepositEth_rev_sig(cf):
    callDataNoSig = cf.vault.fetchDepositEth.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), JUNK_HEX_PAD
    )

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[3] += 1
    # Fetch the deposit
    with reverts(REV_MSG_SIG):
        cf.vault.fetchDepositEth(sigData, JUNK_HEX_PAD)
