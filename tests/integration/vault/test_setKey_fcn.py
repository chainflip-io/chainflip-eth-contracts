from consts import *
from shared_tests import *
from brownie import reverts


# Test changing keys and then calling other fcns

def test_setAggKeyByAggKey_transfer(a, cf):
    # Change agg keys
    setAggKeyWithAggKey_test(cf)

    # Set up the transfer
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)
    startBalVault = cf.vault.balance()
    startBalRecipient = cf.ALICE.balance()
    
    # Check transfer fails with old agg key
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, cf.ALICE, TEST_AMNT)
    with reverts(REV_MSG_SIG):
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, TEST_AMNT)

    # Check transfer with new agg key
    tx = cf.vault.transfer(AGG_SIGNER_2.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, TEST_AMNT)
    
    assert cf.vault.balance() - startBalVault == -TEST_AMNT
    assert cf.ALICE.balance() - startBalRecipient == TEST_AMNT
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)


def test_setAggKeyByAggKey_fetchDeposit_eth_transfer(a, cf, DepositEth):
    recipient = cf.BOB
    recipientStartBal = cf.BOB.balance()

    # Change agg keys
    setAggKeyWithAggKey_test(cf)

    assert cf.BOB.balance() == recipientStartBal
    assert cf.vault.balance() == 0

    # Set up the deposit
    depositAddr = getCreate2Addr(cf.vault.address, JUNK_HEX, DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)

    # Check transfer fails with old agg key
    callDataNoSig = cf.vault.fetchDeposit.encode_input(NULL_SIG_DATA, JUNK_HEX, ETH_ADDR, TEST_AMNT)
    with reverts(REV_MSG_SIG):
        cf.vault.fetchDeposit(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX, ETH_ADDR, TEST_AMNT)
    
    # Fetch the deposit with new agg key
    tx = cf.vault.fetchDeposit(AGG_SIGNER_2.getSigData(callDataNoSig), JUNK_HEX, ETH_ADDR, TEST_AMNT)
    
    assert w3.eth.getBalance(w3.toChecksumAddress(depositAddr)) == 0
    assert cf.vault.balance() == TEST_AMNT
    assert cf.BOB.balance() == recipientStartBal
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)

    # Check transfer fails with old agg key
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, recipient, TEST_AMNT)
    with reverts(REV_MSG_SIG):
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, recipient, TEST_AMNT)

    tx = cf.vault.transfer(AGG_SIGNER_2.getSigData(callDataNoSig), ETH_ADDR, recipient, TEST_AMNT)

    assert w3.eth.getBalance(w3.toChecksumAddress(depositAddr)) == 0
    assert cf.vault.balance() == 0
    assert cf.BOB.balance() == recipientStartBal + TEST_AMNT
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)


def test_setAggKeyByAggKey_fetchDeposit_token_transfer(a, cf, token, DepositToken):
    recipient = cf.BOB
    recipientStartBal = token.balanceOf(cf.BOB)

    # Change agg keys
    setAggKeyWithAggKey_test(cf)

    assert token.balanceOf(cf.BOB) == recipientStartBal
    assert token.balanceOf(cf.vault) == 0

    # Set up the deposit
    depositAddr = getCreate2Addr(cf.vault.address, JUNK_HEX, DepositToken, cleanHexStrPad(token.address) + cleanHexStrPad(TEST_AMNT))
    token.transfer(depositAddr, TEST_AMNT, {'from': cf.DEPLOYER})

    # Check transfer fails with old agg key
    callDataNoSig = cf.vault.fetchDeposit.encode_input(NULL_SIG_DATA, JUNK_HEX, token, TEST_AMNT)

    with reverts(REV_MSG_SIG):
        cf.vault.fetchDeposit(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX, token, TEST_AMNT)

    # Fetch the deposit with new agg key
    tx = cf.vault.fetchDeposit(AGG_SIGNER_2.getSigData(callDataNoSig), JUNK_HEX, token, TEST_AMNT)

    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == TEST_AMNT
    assert token.balanceOf(cf.BOB) == recipientStartBal
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)

    # Check transfer fails with old agg key
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, token, recipient, TEST_AMNT)
    with reverts(REV_MSG_SIG):
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), token, recipient, TEST_AMNT)
    
    # Transfer to recipient
    tx = cf.vault.transfer(AGG_SIGNER_2.getSigData(callDataNoSig), token, recipient, TEST_AMNT)

    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == 0
    assert token.balanceOf(cf.BOB) == recipientStartBal + TEST_AMNT
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)
