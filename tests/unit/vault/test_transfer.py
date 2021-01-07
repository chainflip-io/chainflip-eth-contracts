from consts import *
from brownie import reverts


def test_transfer_eth(a, vault):
    a[0].transfer(vault.address, TEST_AMNT)

    startBalVault = vault.balance()
    startBalRecipient = a[1].balance()
    
    callDataNoSig = vault.transfer.encode_input(0, 0, ETH_ADDR, a[1], TEST_AMNT)
    vault.transfer(*AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, a[1], TEST_AMNT)
    
    assert vault.balance() - startBalVault == -TEST_AMNT
    assert a[1].balance() - startBalRecipient == TEST_AMNT


def test_transfer_token(a, vault, token):
    token.transfer(vault.address, TEST_AMNT, {'from': a[0]})

    startBalVault = token.balanceOf(vault.address)
    startBalRecipient = token.balanceOf(a[1])

    callDataNoSig = vault.transfer.encode_input(0, 0, token.address, a[1], TEST_AMNT)
    vault.transfer(*AGG_SIGNER_1.getSigData(callDataNoSig), token.address, a[1], TEST_AMNT)
    
    assert token.balanceOf(vault.address) - startBalVault == -TEST_AMNT
    assert token.balanceOf(a[1]) - startBalRecipient == TEST_AMNT


def test_transfer_rev_tokenAddr(a, vault):
    callDataNoSig = vault.transfer.encode_input(0, 0, ZERO_ADDR, a[1], TEST_AMNT)

    with reverts(REV_MSG_NZ_ADDR):
        vault.transfer(*AGG_SIGNER_1.getSigData(callDataNoSig), ZERO_ADDR, a[1], TEST_AMNT)


def test_transfer_rev_recipient(a, vault):
    callDataNoSig = vault.transfer.encode_input(0, 0, ETH_ADDR, ZERO_ADDR, TEST_AMNT)

    with reverts(REV_MSG_NZ_ADDR):
        vault.transfer(*AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, ZERO_ADDR, TEST_AMNT)


def test_transfer_rev_amount(a, vault):
    callDataNoSig = vault.transfer.encode_input(0, 0, ETH_ADDR, a[1], 0)

    with reverts(REV_MSG_NZ_UINT):
        vault.transfer(*AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, a[1], 0)