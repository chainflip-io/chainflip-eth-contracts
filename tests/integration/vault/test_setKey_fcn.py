from consts import *
from shared_tests import *
from brownie import reverts


# Test changing keys and then calling other fcns

def test_setAggKeyByAggKey_transfer(a, cf):
    # Change agg keys
    setAggKeyWithAggKey_test(cf)

    # Set up the transfer
    a[0].transfer(cf.vault.address, TEST_AMNT)
    startBalVault = cf.vault.balance()
    startBalRecipient = a[1].balance()
    
    # Check transfer fails with old agg key
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, a[1], TEST_AMNT)
    with reverts(REV_MSG_SIG):
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, a[1], TEST_AMNT)

    # Check transfer with new agg key
    tx = cf.vault.transfer(AGG_SIGNER_2.getSigData(callDataNoSig), ETH_ADDR, a[1], TEST_AMNT)
    
    assert cf.vault.balance() - startBalVault == -TEST_AMNT
    assert a[1].balance() - startBalRecipient == TEST_AMNT
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)


def test_setAggKeyByAggKey_fetchDeposit_eth_transfer(a, cf, DepositEth):
    recipient = a[2]
    recipientStartBal = a[2].balance()

    # Change agg keys
    setAggKeyWithAggKey_test(cf)

    assert a[2].balance() == recipientStartBal
    assert cf.vault.balance() == 0

    # Set up the deposit
    depositAddr = getCreate2Addr(cf.vault.address, JUNK_HEX, DepositEth, "")
    a[0].transfer(depositAddr, TEST_AMNT)

    # Check transfer fails with old agg key
    callDataNoSig = cf.vault.fetchDeposit.encode_input(NULL_SIG_DATA, JUNK_HEX, ETH_ADDR, TEST_AMNT)
    with reverts(REV_MSG_SIG):
        cf.vault.fetchDeposit(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX, ETH_ADDR, TEST_AMNT)
    
    # Fetch the deposit with new agg key
    tx = cf.vault.fetchDeposit(AGG_SIGNER_2.getSigData(callDataNoSig), JUNK_HEX, ETH_ADDR, TEST_AMNT)
    
    assert w3.eth.getBalance(w3.toChecksumAddress(depositAddr)) == 0
    assert cf.vault.balance() == TEST_AMNT
    assert a[2].balance() == recipientStartBal
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)

    # Check transfer fails with old agg key
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, recipient, TEST_AMNT)
    with reverts(REV_MSG_SIG):
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, recipient, TEST_AMNT)

    tx = cf.vault.transfer(AGG_SIGNER_2.getSigData(callDataNoSig), ETH_ADDR, recipient, TEST_AMNT)

    assert w3.eth.getBalance(w3.toChecksumAddress(depositAddr)) == 0
    assert cf.vault.balance() == 0
    assert a[2].balance() == recipientStartBal + TEST_AMNT
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)


def test_setAggKeyByAggKey_fetchDeposit_token_transfer(a, cf, token, DepositToken):
    recipient = a[2]
    recipientStartBal = token.balanceOf(a[2])

    # Change agg keys
    setAggKeyWithAggKey_test(cf)

    assert token.balanceOf(a[2]) == recipientStartBal
    assert token.balanceOf(cf.vault.address) == 0

    # Set up the deposit
    depositAddr = getCreate2Addr(cf.vault.address, JUNK_HEX, DepositToken, cleanHexStrPad(token.address) + cleanHexStrPad(TEST_AMNT))
    token.transfer(depositAddr, TEST_AMNT, {'from': a[0]})

    # Check transfer fails with old agg key
    callDataNoSig = cf.vault.fetchDeposit.encode_input(NULL_SIG_DATA, JUNK_HEX, token.address, TEST_AMNT)

    with reverts(REV_MSG_SIG):
        cf.vault.fetchDeposit(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX, token.address, TEST_AMNT)

    # Fetch the deposit with new agg key
    tx = cf.vault.fetchDeposit(AGG_SIGNER_2.getSigData(callDataNoSig), JUNK_HEX, token.address, TEST_AMNT)

    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault.address) == TEST_AMNT
    assert token.balanceOf(a[2]) == recipientStartBal
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)

    # Check transfer fails with old agg key
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, token.address, recipient, TEST_AMNT)
    with reverts(REV_MSG_SIG):
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), token.address, recipient, TEST_AMNT)
    
    # Transfer to recipient
    tx = cf.vault.transfer(AGG_SIGNER_2.getSigData(callDataNoSig), token.address, recipient, TEST_AMNT)

    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault.address) == 0
    assert token.balanceOf(a[2]) == recipientStartBal + TEST_AMNT
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)
