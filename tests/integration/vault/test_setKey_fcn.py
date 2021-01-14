from consts import *
from shared_tests import *
from brownie import reverts


# Test changing keys and then calling other fcns

def test_setAggKeyByAggKey_transfer(a, vault):
    # Change agg keys
    testSetAggKeyByAggKey(vault)

    # Set up the transfer
    a[0].transfer(vault.address, TEST_AMNT)
    startBalVault = vault.balance()
    startBalRecipient = a[1].balance()

    # Check transfer fails with old agg key
    callDataNoSig = vault.transfer.encode_input(0, 0, ETH_ADDR, a[1], TEST_AMNT)
    with reverts(REV_MSG_SIG):
        vault.transfer(*AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, a[1], TEST_AMNT)

    # Check transfer with new agg key
    tx = vault.transfer(*AGG_SIGNER_2.getSigData(callDataNoSig), ETH_ADDR, a[1], TEST_AMNT)

    assert vault.balance() - startBalVault == -TEST_AMNT
    assert a[1].balance() - startBalRecipient == TEST_AMNT
    txTimeTest(vault.getLastValidateTime(), tx)


def test_setAggKeyByAggKey_fetchDeposit_eth_transfer(a, vault, DepositEth):
    recipient = a[2]
    recipientStartBal = a[2].balance()

    # Change agg keys
    testSetAggKeyByAggKey(vault)

    assert a[2].balance() == recipientStartBal
    assert vault.balance() == 0

    # Set up the deposit
    depositAddr = getCreate2Addr(vault.address, SWAP_ID_HEX, DepositEth, "")
    a[0].transfer(depositAddr, TEST_AMNT)

    # Check transfer fails with old agg key
    callDataNoSig = vault.fetchDeposit.encode_input(0, 0, SWAP_ID_HEX, ETH_ADDR)
    with reverts(REV_MSG_SIG):
        vault.fetchDeposit(*AGG_SIGNER_1.getSigData(callDataNoSig), SWAP_ID_HEX, ETH_ADDR)

    # Fetch the deposit with new agg key
    tx = vault.fetchDeposit(*AGG_SIGNER_2.getSigData(callDataNoSig), SWAP_ID_HEX, ETH_ADDR)

    assert w3.eth.getBalance(w3.toChecksumAddress(depositAddr)) == 0
    assert vault.balance() == TEST_AMNT
    assert a[2].balance() == recipientStartBal
    txTimeTest(vault.getLastValidateTime(), tx)

    # Check transfer fails with old agg key
    callDataNoSig = vault.transfer.encode_input(0, 0, ETH_ADDR, recipient, TEST_AMNT)
    with reverts(REV_MSG_SIG):
        vault.transfer(*AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, recipient, TEST_AMNT)

    tx = vault.transfer(*AGG_SIGNER_2.getSigData(callDataNoSig), ETH_ADDR, recipient, TEST_AMNT)

    assert w3.eth.getBalance(w3.toChecksumAddress(depositAddr)) == 0
    assert vault.balance() == 0
    assert a[2].balance() == recipientStartBal + TEST_AMNT
    txTimeTest(vault.getLastValidateTime(), tx)


def test_setAggKeyByAggKey_fetchDeposit_token_transfer(a, vault, token, DepositToken):
    recipient = a[2]
    recipientStartBal = token.balanceOf(a[2])

    # Change agg keys
    testSetAggKeyByAggKey(vault)

    assert token.balanceOf(a[2]) == recipientStartBal
    assert token.balanceOf(vault.address) == 0

    # Set up the deposit
    depositAddr = getCreate2Addr(vault.address, SWAP_ID_HEX, DepositToken, cleanHexStrPad(token.address))
    token.transfer(depositAddr, TEST_AMNT, {'from': a[0]})

    # Check transfer fails with old agg key
    callDataNoSig = vault.fetchDeposit.encode_input(0, 0, SWAP_ID_HEX, token.address)

    with reverts(REV_MSG_SIG):
        vault.fetchDeposit(*AGG_SIGNER_1.getSigData(callDataNoSig), SWAP_ID_HEX, token.address)

    # Fetch the deposit with new agg key
    tx = vault.fetchDeposit(*AGG_SIGNER_2.getSigData(callDataNoSig), SWAP_ID_HEX, token.address)

    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(vault.address) == TEST_AMNT
    assert token.balanceOf(a[2]) == recipientStartBal
    txTimeTest(vault.getLastValidateTime(), tx)

    # Check transfer fails with old agg key
    callDataNoSig = vault.transfer.encode_input(0, 0, token.address, recipient, TEST_AMNT)
    with reverts(REV_MSG_SIG):
        vault.transfer(*AGG_SIGNER_1.getSigData(callDataNoSig), token.address, recipient, TEST_AMNT)

    # Transfer to recipient
    tx = vault.transfer(*AGG_SIGNER_2.getSigData(callDataNoSig), token.address, recipient, TEST_AMNT)

    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(vault.address) == 0
    assert token.balanceOf(a[2]) == recipientStartBal + TEST_AMNT
    txTimeTest(vault.getLastValidateTime(), tx)
