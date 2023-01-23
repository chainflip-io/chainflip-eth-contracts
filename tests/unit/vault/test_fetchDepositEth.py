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


# Redeploy a depositNATIVE contract in the same address as the previous one. This is in case
# an attacker tries to grief the protocol by sending a small amount to an address where
# the CFE is expecting the user's input swap amount to be deposited. We need to then
# be able to redeploy the contract in the same address to be able to fetch the funds.
def test_fetchDepositNative_grief(cf, DepositNative):
    assert cf.vault.balance() == 0

    addr0 = fetchDepositNative(cf, cf.vault, DepositNative)
    assert cf.vault.balance() == TEST_AMNT

    addr1 = fetchDepositNative(cf, cf.vault, DepositNative, amount=TEST_AMNT * 200)
    assert cf.vault.balance() == TEST_AMNT * (200 + 1)

    # Check addresses are the same
    assert addr0 == addr1
