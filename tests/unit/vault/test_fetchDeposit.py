import umbral
from umbral import pre, keys, signing
from brownie import web3 as w3
from utils import *
from crypto import *
from consts import *


def test_fetchDeposit_eth(a, vault, DepositEth):
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(vault.address, SWAP_ID_HEX, DepositEth, "")
    a[0].transfer(depositAddr, TEST_AMNT)

    # Sign the tx without a msgHash or sig
    callDataNoSig = vault.fetchDeposit.encode_input(SWAP_ID_HEX, ETH_ADDR, TEST_AMNT, "", "")
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)

    # Fetch the deposit
    tx = vault.fetchDeposit(SWAP_ID_HEX, ETH_ADDR, TEST_AMNT, *sigData)
    assert vault.balance() == TEST_AMNT


def test_fetchDeposit_token(a, vault, token, DepositToken):
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(vault.address, SWAP_ID_HEX, DepositToken, cleanHexStrPad(token.address) + cleanHexStrPad(TEST_AMNT))
    token.transfer(depositAddr, TEST_AMNT, {'from': a[0]})

    # Sign the tx without a msgHash or sig
    callDataNoSig = vault.fetchDeposit.encode_input(SWAP_ID_HEX, token.address, TEST_AMNT, "", "")
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    
    # Fetch the deposit
    tx = vault.fetchDeposit(SWAP_ID_HEX, token.address, TEST_AMNT, *sigData)
