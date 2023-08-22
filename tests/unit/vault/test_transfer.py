from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy


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


# token doesn't have a fallback function for receiving native, so should fail
def test_transferfallback_native_fails_recipient(cf, token):
    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT)

    args = [[NATIVE_ADDR, token.address, TEST_AMNT]]
    with reverts(REV_MSG_TRANSFER_FALLBACK):
        signed_call_cf(cf, cf.vault.transferFallback, *args)


def test_transfer_native_deposit_address(cf, Deposit):
    tx = signed_call_cf(
        cf,
        cf.vault.deployAndFetchBatch,
        [[JUNK_HEX, NATIVE_ADDR]],
    )
    depositAddr = getCreate2Addr(
        cf.vault.address,
        cleanHexStrPad(JUNK_HEX),
        Deposit,
        cleanHexStrPad(NATIVE_ADDR),
    )
    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT)

    startBalVault = cf.vault.balance()
    startBalRecipient = web3.eth.get_balance(depositAddr)

    args = [[NATIVE_ADDR, depositAddr, TEST_AMNT]]
    tx = signed_call_cf(cf, cf.vault.transfer, *args)
    assert "TransferNativeFailed" not in tx.events
    # Transfer is succesfull but it will be funneled back to the vault
    assert cf.vault.balance() == startBalVault
    assert web3.eth.get_balance(depositAddr) == startBalRecipient


# Trying to send native when there's none in the Vault
def test_transfer_native_fails_not_enough_native(cf):
    startBalRecipient = cf.ALICE.balance()

    args = [[NATIVE_ADDR, cf.ALICE, TEST_AMNT]]
    tx = signed_call_cf(cf, cf.vault.transfer, *args)

    assert tx.events["TransferNativeFailed"][0].values() == [cf.ALICE, TEST_AMNT]
    assert cf.vault.balance() == 0
    assert cf.ALICE.balance() == startBalRecipient

    with reverts(REV_MSG_TRANSFER_FALLBACK):
        signed_call_cf(cf, cf.vault.transferFallback, *args)


def test_transfer_token(cf, token):
    transfer_token(cf, token, cf.vault.transfer)


def test_transfer_fallback_token(cf, token):
    transfer_token(cf, token, cf.vault.transferFallback)


def transfer_token(cf, token, fcn):
    token.transfer(cf.vault, TEST_AMNT, {"from": cf.SAFEKEEPER})

    startBalVault = token.balanceOf(cf.vault)
    startBalRecipient = token.balanceOf(cf.ALICE)

    args = [[token, cf.ALICE, TEST_AMNT]]
    signed_call_cf(cf, fcn, *args)

    assert token.balanceOf(cf.vault) - startBalVault == -TEST_AMNT
    assert token.balanceOf(cf.ALICE) - startBalRecipient == TEST_AMNT


def test_transfer_rev_tokenAddr(cf):
    transfer_rev_tokenAddr(cf, cf.vault.transfer)


def test_transferFallback_rev_tokenAddr(cf):
    transfer_rev_tokenAddr(cf, cf.vault.transferFallback)


def transfer_rev_tokenAddr(cf, fcn):
    with reverts(REV_MSG_NZ_ADDR):
        args = [[ZERO_ADDR, cf.ALICE, TEST_AMNT]]
        signed_call_cf(cf, fcn, *args)


def test_transfer_rev_recipient(cf):
    transfer_rev_tokenAddr(cf, cf.vault.transfer)


def test_transferFallback_rev_recipient(cf):
    transfer_rev_tokenAddr(cf, cf.vault.transferFallback)


def transfer_rev_recipient(cf, fcn):
    with reverts(REV_MSG_NZ_ADDR):
        args = [[NATIVE_ADDR, ZERO_ADDR, TEST_AMNT]]
        signed_call_cf(cf, fcn, *args)


def test_transfer_rev_amount(cf):
    transfer_rev_amount(cf, cf.vault.transfer)


def test_transferFallback_rev_amount(cf):
    transfer_rev_amount(cf, cf.vault.transferFallback)


def transfer_rev_amount(cf, fcn):
    with reverts(REV_MSG_NZ_UINT):
        args = [[NATIVE_ADDR, cf.ALICE, 0]]
        signed_call_cf(cf, fcn, *args)


def test_transfer_rev_sig(cf):
    transfer_rev_sig(cf, cf.vault.transfer)


def test_transfer_rev_sig(cf):
    transfer_rev_sig(cf, cf.vault.transferFallback)


def transfer_rev_sig(cf, fcn):
    args = [[NATIVE_ADDR, cf.ALICE, TEST_AMNT]]
    sigData = AGG_SIGNER_1.getSigDataWithNonces(cf.keyManager, fcn, nonces, *args)

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


def test_transferFallback_usdt(cf, mockUSDT):
    args = [[mockUSDT.address, cf.ALICE, TEST_AMNT_USDC]]
    with reverts():
        signed_call_cf(cf, cf.vault.transferFallback, *args)


def test_transfer_usdt(cf, mockUSDT):
    mockUSDT.transfer(cf.vault, TEST_AMNT_USDC, {"from": cf.SAFEKEEPER})
    args = [[mockUSDT.address, cf.ALICE, TEST_AMNT_USDC]]
    iniBal_vault = mockUSDT.balanceOf(cf.vault)
    iniBal_Alice = mockUSDT.balanceOf(cf.ALICE)
    assert iniBal_vault == TEST_AMNT_USDC

    tx = signed_call_cf(cf, cf.vault.transfer, *args)

    assert iniBal_vault - TEST_AMNT_USDC == mockUSDT.balanceOf(cf.vault)
    assert iniBal_Alice + TEST_AMNT_USDC == mockUSDT.balanceOf(cf.ALICE)

    assert ["TransferTokenFailed"] not in tx.events


@given(
    st_amount=strategy("uint", max_value=TEST_AMNT),
    st_sender=strategy("address"),
)
def test_receive_vault(cf, st_sender, st_amount):
    tx = st_sender.transfer(cf.vault, st_amount)
    assert tx.events["FetchedNative"][0].values() == [st_sender, st_amount]
