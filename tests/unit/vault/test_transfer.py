from consts import *
from shared_tests import *
from brownie import reverts


def test_transfer_native(cf):
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)
    transfer_native(cf, cf.vault, cf.ALICE, TEST_AMNT)


# token doesn't have a fallback function for receiving native, so should fail
def test_transfer_native_fails_recipient(cf, token):
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)

    startBalVault = cf.vault.balance()
    startBalRecipient = cf.ALICE.balance()

    args = [[NATIVE_ADDR, token, TEST_AMNT]]
    tx = signed_call_cf(cf, cf.vault.transfer, *args)

    assert tx.events["TransferNativeFailed"][0].values() == [token, TEST_AMNT]
    assert cf.vault.balance() == startBalVault
    assert cf.ALICE.balance() == startBalRecipient


# Trying to send native when there's none in the Vault
def test_transfer_native_fails_not_enough_native(cf):
    startBalRecipient = cf.ALICE.balance()

    args = [[NATIVE_ADDR, cf.ALICE, TEST_AMNT]]
    tx = signed_call_cf(cf, cf.vault.transfer, *args)

    assert tx.events["TransferNativeFailed"][0].values() == [cf.ALICE, TEST_AMNT]
    assert cf.vault.balance() == 0
    assert cf.ALICE.balance() == startBalRecipient


def test_transfer_token(cf, token):
    token.transfer(cf.vault, TEST_AMNT, {"from": cf.DEPLOYER})

    startBalVault = token.balanceOf(cf.vault)
    startBalRecipient = token.balanceOf(cf.ALICE)

    args = [[token, cf.ALICE, TEST_AMNT]]
    signed_call_cf(cf, cf.vault.transfer, *args)

    assert token.balanceOf(cf.vault) - startBalVault == -TEST_AMNT
    assert token.balanceOf(cf.ALICE) - startBalRecipient == TEST_AMNT


def test_transfer_rev_tokenAddr(cf):
    with reverts(REV_MSG_NZ_ADDR):
        args = [[ZERO_ADDR, cf.ALICE, TEST_AMNT]]
        signed_call_cf(cf, cf.vault.transfer, *args)


def test_transfer_rev_recipient(cf):
    with reverts(REV_MSG_NZ_ADDR):
        args = [[NATIVE_ADDR, ZERO_ADDR, TEST_AMNT]]
        signed_call_cf(cf, cf.vault.transfer, *args)


def test_transfer_rev_amount(cf):
    with reverts(REV_MSG_NZ_UINT):
        args = [[NATIVE_ADDR, cf.ALICE, 0]]
        signed_call_cf(cf, cf.vault.transfer, *args)


def test_transfer_rev_msgHash(cf):
    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        [NATIVE_ADDR, cf.ALICE, TEST_AMNT],
    )
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[2] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.vault.transfer(sigData, [NATIVE_ADDR, cf.ALICE, TEST_AMNT])


def test_transfer_rev_sig(cf):
    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        [NATIVE_ADDR, cf.ALICE, TEST_AMNT],
    )
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[3] += 1

    with reverts(REV_MSG_SIG):
        cf.vault.transfer(sigData, [NATIVE_ADDR, cf.ALICE, TEST_AMNT])
