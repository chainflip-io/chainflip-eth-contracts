from consts import *
from shared_tests import *
from brownie import reverts


def test_transfer_native(cf):
    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT)
    transfer_native(cf, cf.vault, cf.ALICE, TEST_AMNT)


# token doesn't have a fallback function for receiving native, so should fail
def test_transfer_native_fails_recipient(cf, token):
    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT)

    startBalVault = cf.vault.balance()
    startBalRecipient = cf.ALICE.balance()

    args = [[NATIVE_ADDR, token.address, TEST_AMNT]]
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
    token.transfer(cf.vault, TEST_AMNT, {"from": cf.SAFEKEEPER})

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


def test_transfer_rev_sig(cf):
    args = [[NATIVE_ADDR, cf.ALICE, TEST_AMNT]]
    sigData = AGG_SIGNER_1.getSigDataWithNonces(
        cf.keyManager, cf.vault.transfer, nonces, *args
    )

    sigData_modif = sigData[:]
    sigData_modif[0] += 1
    with reverts(REV_MSG_SIG):
        cf.vault.transfer(sigData_modif, *args, {"from": cf.ALICE})

    sigData_modif = sigData[:]
    sigData_modif[1] += 1
    with reverts(REV_MSG_SIG):
        cf.vault.transfer(sigData_modif, *args, {"from": cf.ALICE})

    sigData_modif = sigData[:]
    sigData_modif[2] = NON_ZERO_ADDR
    with reverts(REV_MSG_SIG):
        cf.vault.transfer(sigData_modif, *args, {"from": cf.ALICE})


def test_transfer_rev_usdt(cf, mockUSDT, utils):
    args = [[mockUSDT.address, cf.ALICE, TEST_AMNT_USDC]]
    tx = signed_call_cf(cf, cf.vault.transfer, *args)

    assert tx.events["TransferTokenFailed"]["recipient"] == cf.ALICE
    assert tx.events["TransferTokenFailed"]["amount"] == TEST_AMNT_USDC
    assert tx.events["TransferTokenFailed"]["token"] == mockUSDT.address
    assert (
        utils.decodeRevertData(tx.events["TransferTokenFailed"]["reason"])
        == REV_MSG_ERC20_EXCEED_BAL
    )


def test_transfer_usdt(cf, mockUSDT):
    print(mockUSDT.balanceOf(cf.SAFEKEEPER))
    mockUSDT.transfer(cf.vault, TEST_AMNT_USDC, {"from": cf.SAFEKEEPER})
    args = [[mockUSDT.address, cf.ALICE, TEST_AMNT_USDC]]
    iniBal_vault = mockUSDT.balanceOf(cf.vault)
    iniBal_Alice = mockUSDT.balanceOf(cf.ALICE)
    assert iniBal_vault == TEST_AMNT_USDC

    tx = signed_call_cf(cf, cf.vault.transfer, *args)

    assert iniBal_vault - TEST_AMNT_USDC == mockUSDT.balanceOf(cf.vault)
    assert iniBal_Alice + TEST_AMNT_USDC == mockUSDT.balanceOf(cf.ALICE)

    assert ["TransferTokenFailed"] not in tx.events
