from consts import *
from shared_tests import *
from brownie import reverts


# Test changing keys and then calling other fcns

def test_setAggKeyByAggKey_transfer(cf):
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


def test_setAggKeyByAggKey_fetchDepositEth_transfer(cf, DepositEth):
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
    callDataNoSig = cf.vault.fetchDepositEth.encode_input(NULL_SIG_DATA, JUNK_HEX)
    with reverts(REV_MSG_SIG):
        cf.vault.fetchDepositEth(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX)
    
    # Fetch the deposit with new agg key
    tx = cf.vault.fetchDepositEth(AGG_SIGNER_2.getSigData(callDataNoSig), JUNK_HEX)
    
    assert web3.eth.getBalance(web3.toChecksumAddress(depositAddr)) == 0
    assert cf.vault.balance() == TEST_AMNT
    assert cf.BOB.balance() == recipientStartBal
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)

    # Check transfer fails with old agg key
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, recipient, TEST_AMNT)
    with reverts(REV_MSG_SIG):
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, recipient, TEST_AMNT)

    tx = cf.vault.transfer(AGG_SIGNER_2.getSigData(callDataNoSig), ETH_ADDR, recipient, TEST_AMNT)

    assert web3.eth.getBalance(web3.toChecksumAddress(depositAddr)) == 0
    assert cf.vault.balance() == 0
    assert cf.BOB.balance() == recipientStartBal + TEST_AMNT
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)


def test_setAggKeyByAggKey_fetchDepositToken_transfer(cf, token, DepositToken):
    recipient = cf.BOB
    recipientStartBal = token.balanceOf(cf.BOB)

    # Change agg keys
    setAggKeyWithAggKey_test(cf)

    assert token.balanceOf(cf.BOB) == recipientStartBal
    assert token.balanceOf(cf.vault) == 0

    # Set up the deposit
    depositAddr = getCreate2Addr(cf.vault.address, JUNK_HEX, DepositToken, cleanHexStrPad(token.address))
    token.transfer(depositAddr, TEST_AMNT, {'from': cf.DEPLOYER})

    # Check transfer fails with old agg key
    callDataNoSig = cf.vault.fetchDepositToken.encode_input(NULL_SIG_DATA, JUNK_HEX, token)

    with reverts(REV_MSG_SIG):
        cf.vault.fetchDepositToken(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX, token)

    # Fetch the deposit with new agg key
    tx = cf.vault.fetchDepositToken(AGG_SIGNER_2.getSigData(callDataNoSig), JUNK_HEX, token)

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


def test_setAggKeyByAggKey_fetchDepositEthBatch_transfer_fetchDepositBatchBatch_transfer(cf, token, DepositEth, DepositToken):
    # Change agg keys
    setAggKeyWithAggKey_test(cf)
    
    # Get the address to deposit to and deposit
    swapIDs = [cleanHexStrPad(0), cleanHexStrPad(1)]
    depositAddr = getCreate2Addr(cf.vault.address, swapIDs[0], DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)
    depositAddr2 = getCreate2Addr(cf.vault.address, swapIDs[1], DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr2, 2 * TEST_AMNT)

    assert cf.vault.balance() == 0

    callDataNoSig = cf.vault.fetchDepositEthBatch.encode_input(NULL_SIG_DATA, swapIDs)

    # Check fetchDepositEthBatch fails with old agg key
    with reverts(REV_MSG_SIG):
        cf.vault.fetchDepositEthBatch(AGG_SIGNER_1.getSigData(callDataNoSig), swapIDs)
    
    # Fetch the deposits with new agg key
    cf.vault.fetchDepositEthBatch(AGG_SIGNER_2.getSigData(callDataNoSig), swapIDs)

    assert web3.eth.getBalance(web3.toChecksumAddress(depositAddr)) == 0
    assert web3.eth.getBalance(web3.toChecksumAddress(depositAddr2)) == 0
    assert cf.vault.balance() == 3 * TEST_AMNT

    # Transfer the eth out the vault
    ethStartBalVault = cf.vault.balance()
    tokenStartBalRecipient = cf.ALICE.balance()

    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, cf.ALICE, TEST_AMNT)

    # Check transfer fails with old agg key
    with reverts(REV_MSG_SIG):
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, TEST_AMNT)

    # Transfer with new agg key
    cf.vault.transfer(AGG_SIGNER_2.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, TEST_AMNT)
    
    assert cf.vault.balance() - ethStartBalVault == -TEST_AMNT
    assert cf.ALICE.balance() - tokenStartBalRecipient == TEST_AMNT

    # Transferring out again should fail
    # No specific error message for failing eth transfer
    with reverts():
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, (2 * TEST_AMNT) + 1)
    
    # Fetch token deposit
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, swapIDs[0], DepositToken, cleanHexStrPad(token.address))
    token.transfer(depositAddr, TEST_AMNT, {'from': cf.DEPLOYER})
    depositAddr2 = getCreate2Addr(cf.vault.address, swapIDs[1], DepositToken, cleanHexStrPad(token.address))
    cf.DEPLOYER.transfer(depositAddr2, 2 * TEST_AMNT)
    token.transfer(depositAddr2, 2 * TEST_AMNT, {'from': cf.DEPLOYER})

    assert token.balanceOf(cf.vault) == 0

    callDataNoSig = cf.vault.fetchDepositTokenBatch.encode_input(NULL_SIG_DATA, swapIDs, [token, token])

    # Check fetchDepositTokenBatch fails with old agg key
    with reverts(REV_MSG_SIG):
        cf.vault.fetchDepositTokenBatch(AGG_SIGNER_1.getSigData(callDataNoSig), swapIDs, [token, token])
    
    # Fetch the deposits with new agg key
    cf.vault.fetchDepositTokenBatch(AGG_SIGNER_2.getSigData(callDataNoSig), swapIDs, [token, token])
    
    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == 3 * TEST_AMNT

    # Transfer half the tokens in the vault
    amount = TEST_AMNT * 1.5
    tokenStartBalVault = token.balanceOf(cf.vault)
    tokenStartBalRecipient = token.balanceOf(cf.ALICE)

    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, token, cf.ALICE, amount)
    # Check transfer fails with old agg key
    with reverts(REV_MSG_SIG):
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), token, cf.ALICE, amount)
    
    cf.vault.transfer(AGG_SIGNER_2.getSigData(callDataNoSig), token, cf.ALICE, amount)
    
    assert token.balanceOf(cf.vault) - tokenStartBalVault == -amount
    assert token.balanceOf(cf.ALICE) - tokenStartBalRecipient == amount