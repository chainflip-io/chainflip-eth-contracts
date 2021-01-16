import umbral
from brownie import reverts, web3 as w3
from consts import *


def test_fetchDeposit_eth(a, cf, DepositEth):
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, JUNK_HEX, DepositEth, "")
    a[0].transfer(depositAddr, TEST_AMNT)

    assert cf.vault.balance() == 0

    # Sign the tx without a msgHash or sig
    callDataNoSig = cf.vault.fetchDeposit.encode_input(NULL_SIG_DATA, JUNK_HEX, ETH_ADDR, TEST_AMNT)

    # Fetch the deposit
    cf.vault.fetchDeposit(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX, ETH_ADDR, TEST_AMNT)
    assert w3.eth.getBalance(w3.toChecksumAddress(depositAddr)) == 0
    assert cf.vault.balance() == TEST_AMNT


def test_fetchDeposit_token(a, cf, token, DepositToken):
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, JUNK_HEX, DepositToken, cleanHexStrPad(token.address) + cleanHexStrPad(TEST_AMNT))
    token.transfer(depositAddr, TEST_AMNT, {'from': a[0]})

    assert token.balanceOf(cf.vault.address) == 0

    # Sign the tx without a msgHash or sig
    callDataNoSig = cf.vault.fetchDeposit.encode_input(NULL_SIG_DATA, JUNK_HEX, token.address, TEST_AMNT)
    
    # Fetch the deposit
    cf.vault.fetchDeposit(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX, token.address, TEST_AMNT)
    
    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault.address) == TEST_AMNT


def test_fetchDeposit_rev_swapID(cf):
    callDataNoSig = cf.vault.fetchDeposit.encode_input(NULL_SIG_DATA, "", ETH_ADDR, TEST_AMNT)

    with reverts(REV_MSG_NZ_BYTES32):
        cf.vault.fetchDeposit(AGG_SIGNER_1.getSigData(callDataNoSig), "", ETH_ADDR, TEST_AMNT)


def test_fetchDeposit_rev_tokenAddr(cf):
    callDataNoSig = cf.vault.fetchDeposit.encode_input(NULL_SIG_DATA, JUNK_HEX, ZERO_ADDR, TEST_AMNT)

    with reverts(REV_MSG_NZ_ADDR):
        cf.vault.fetchDeposit(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX, ZERO_ADDR, TEST_AMNT)


def test_fetchDeposit_rev_amount(cf):
    callDataNoSig = cf.vault.fetchDeposit.encode_input(NULL_SIG_DATA, JUNK_HEX, ETH_ADDR, 0)

    with reverts(REV_MSG_NZ_UINT):
        cf.vault.fetchDeposit(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX, ETH_ADDR, 0)


def test_fetchDeposit_rev_msgHash(cf):
    callDataNoSig = cf.vault.fetchDeposit.encode_input(NULL_SIG_DATA, JUNK_HEX, ETH_ADDR, TEST_AMNT)

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[0] += 1
    # Fetch the deposit
    with reverts(REV_MSG_MSGHASH):
        cf.vault.fetchDeposit(sigData, JUNK_HEX, ETH_ADDR, TEST_AMNT)


def test_fetchDeposit_rev_sig(cf):
    callDataNoSig = cf.vault.fetchDeposit.encode_input(NULL_SIG_DATA, JUNK_HEX, ETH_ADDR, TEST_AMNT)

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[1] += 1
    # Fetch the deposit
    with reverts(REV_MSG_SIG):
        cf.vault.fetchDeposit(sigData, JUNK_HEX, ETH_ADDR, TEST_AMNT)
