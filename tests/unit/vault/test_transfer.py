from consts import *
from brownie import reverts


def test_transfer_eth(a, cf):
    a[0].transfer(cf.vault.address, TEST_AMNT)

    startBalVault = cf.vault.balance()
    startBalRecipient = a[1].balance()
    
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, a[1], TEST_AMNT)
    cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, a[1], TEST_AMNT)
    
    assert cf.vault.balance() - startBalVault == -TEST_AMNT
    assert a[1].balance() - startBalRecipient == TEST_AMNT


def test_transfer_token(a, cf, token):
    token.transfer(cf.vault.address, TEST_AMNT, {'from': a[0]})

    startBalVault = token.balanceOf(cf.vault.address)
    startBalRecipient = token.balanceOf(a[1])

    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, token.address, a[1], TEST_AMNT)
    cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), token.address, a[1], TEST_AMNT)
    
    assert token.balanceOf(cf.vault.address) - startBalVault == -TEST_AMNT
    assert token.balanceOf(a[1]) - startBalRecipient == TEST_AMNT


def test_transfer_rev_tokenAddr(a, cf):
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ZERO_ADDR, a[1], TEST_AMNT)

    with reverts(REV_MSG_NZ_ADDR):
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ZERO_ADDR, a[1], TEST_AMNT)


def test_transfer_rev_recipient(a, cf):
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, ZERO_ADDR, TEST_AMNT)

    with reverts(REV_MSG_NZ_ADDR):
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, ZERO_ADDR, TEST_AMNT)


def test_transfer_rev_amount(a, cf):
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, a[1], 0)

    with reverts(REV_MSG_NZ_UINT):
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, a[1], 0)


def test_transfer_rev_msgHash(a, cf):
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, a[1], TEST_AMNT)
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[0] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.vault.transfer(sigData, ETH_ADDR, a[1], TEST_AMNT)


def test_transfer_rev_sig(a, cf):
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, a[1], TEST_AMNT)
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[1] += 1

    with reverts(REV_MSG_SIG):
        cf.vault.transfer(sigData, ETH_ADDR, a[1], TEST_AMNT)