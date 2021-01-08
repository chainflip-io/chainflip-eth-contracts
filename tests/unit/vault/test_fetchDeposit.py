import umbral
from brownie import reverts, web3 as w3
from consts import *


def test_fetchDeposit_eth(a, vault, DepositEth):
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(vault.address, SWAP_ID_HEX, DepositEth, "")
    a[0].transfer(depositAddr, TEST_AMNT)

    assert vault.balance() == 0

    # Sign the tx without a msgHash or sig
    callDataNoSig = vault.fetchDeposit.encode_input(0, 0, SWAP_ID_HEX, ETH_ADDR, TEST_AMNT)

    # Fetch the deposit
    vault.fetchDeposit(*AGG_SIGNER_1.getSigData(callDataNoSig), SWAP_ID_HEX, ETH_ADDR, TEST_AMNT)
    assert w3.eth.getBalance(w3.toChecksumAddress(depositAddr)) == 0
    assert vault.balance() == TEST_AMNT


def test_fetchDeposit_token(a, vault, token, DepositToken):
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(vault.address, SWAP_ID_HEX, DepositToken, cleanHexStrPad(token.address) + cleanHexStrPad(TEST_AMNT))
    token.transfer(depositAddr, TEST_AMNT, {'from': a[0]})

    assert token.balanceOf(vault.address) == 0

    # Sign the tx without a msgHash or sig
    callDataNoSig = vault.fetchDeposit.encode_input(0, 0, SWAP_ID_HEX, token.address, TEST_AMNT)
    
    # Fetch the deposit
    vault.fetchDeposit(*AGG_SIGNER_1.getSigData(callDataNoSig), SWAP_ID_HEX, token.address, TEST_AMNT)
    
    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(vault.address) == TEST_AMNT


def test_fetchDeposit_rev_swapID(vault):
    callDataNoSig = vault.fetchDeposit.encode_input(0, 0, "", ETH_ADDR, TEST_AMNT)

    with reverts(REV_MSG_NZ_BYTES32):
        vault.fetchDeposit(*AGG_SIGNER_1.getSigData(callDataNoSig), "", ETH_ADDR, TEST_AMNT)


def test_fetchDeposit_rev_tokenAddr(vault):
    callDataNoSig = vault.fetchDeposit.encode_input(0, 0, SWAP_ID_HEX, ZERO_ADDR, TEST_AMNT)

    with reverts(REV_MSG_NZ_ADDR):
        vault.fetchDeposit(*AGG_SIGNER_1.getSigData(callDataNoSig), SWAP_ID_HEX, ZERO_ADDR, TEST_AMNT)


def test_fetchDeposit_rev_amount(vault):
    callDataNoSig = vault.fetchDeposit.encode_input(0, 0, SWAP_ID_HEX, ETH_ADDR, 0)

    with reverts(REV_MSG_NZ_UINT):
        vault.fetchDeposit(*AGG_SIGNER_1.getSigData(callDataNoSig), SWAP_ID_HEX, ETH_ADDR, 0)


# Testing to see if this test affects `bownie test --coverage`. Oddly, it increases the coverage
# of SchnorrSECP256K1 but not Vault - probably a bug with in Brownie
def test_fetchDeposit_rev_sig(vault):
    callDataNoSig = vault.fetchDeposit.encode_input(0, 0, SWAP_ID_HEX, ETH_ADDR, TEST_AMNT)

    sigData = list(AGG_SIGNER_1.getSigData(callDataNoSig))
    sigData[1] = Signer.Q_INT
    # Fetch the deposit
    with reverts(REV_MSG_SIG_LESS_Q):
#         vault.fetchDeposit(*sigData, SWAP_ID_HEX, ETH_ADDR, TEST_AMNT)
