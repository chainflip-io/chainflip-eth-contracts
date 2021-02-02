from brownie import reverts, web3 as w3
from consts import *


def test_fetchDepositToken(a, cf, token, DepositToken):
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, JUNK_HEX, DepositToken, cleanHexStrPad(token.address))
    token.transfer(depositAddr, TEST_AMNT, {'from': cf.DEPLOYER})

    assert token.balanceOf(cf.vault) == 0

    # Sign the tx without a msgHash or sig
    callDataNoSig = cf.vault.fetchDepositToken.encode_input(NULL_SIG_DATA, JUNK_HEX, token)
    
    # Fetch the deposit
    cf.vault.fetchDepositToken(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX, token)
    
    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == TEST_AMNT


def test_fetchDepositToken_rev_swapID(cf):
    callDataNoSig = cf.vault.fetchDepositToken.encode_input(NULL_SIG_DATA, "", ETH_ADDR)

    with reverts(REV_MSG_NZ_BYTES32):
        cf.vault.fetchDepositToken(AGG_SIGNER_1.getSigData(callDataNoSig), "", ETH_ADDR)


def test_fetchDepositToken_rev_tokenAddr(cf):
    callDataNoSig = cf.vault.fetchDepositToken.encode_input(NULL_SIG_DATA, JUNK_HEX, ZERO_ADDR)

    with reverts(REV_MSG_NZ_ADDR):
        cf.vault.fetchDepositToken(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX, ZERO_ADDR)


def test_fetchDepositToken_rev_msgHash(cf):
    callDataNoSig = cf.vault.fetchDepositToken.encode_input(NULL_SIG_DATA, JUNK_HEX, ETH_ADDR)

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[0] += 1
    # Fetch the deposit
    with reverts(REV_MSG_MSGHASH):
        cf.vault.fetchDepositToken(sigData, JUNK_HEX, ETH_ADDR)


def test_fetchDepositToken_rev_sig(cf):
    callDataNoSig = cf.vault.fetchDepositToken.encode_input(NULL_SIG_DATA, JUNK_HEX, ETH_ADDR)

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[1] += 1
    # Fetch the deposit
    with reverts(REV_MSG_SIG):
        cf.vault.fetchDepositToken(sigData, JUNK_HEX, ETH_ADDR)