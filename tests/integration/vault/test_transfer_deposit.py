from consts import *
from brownie import reverts


def test_fetchDepositEth_transfer_fetchDepositToken_transfer(cf, token, DepositEth, DepositToken):
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, JUNK_HEX, DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)

    assert cf.vault.balance() == 0

    callDataNoSig = cf.vault.fetchDepositEth.encode_input(NULL_SIG_DATA, JUNK_HEX)
    cf.vault.fetchDepositEth(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX)

    assert web3.eth.getBalance(web3.toChecksumAddress(depositAddr)) == 0
    assert cf.vault.balance() == TEST_AMNT

    # Transfer the eth out the vault
    ethStartBalVault = cf.vault.balance()
    tokenStartBalRecipient = cf.ALICE.balance()

    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, cf.ALICE, TEST_AMNT)
    cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, TEST_AMNT)
    
    assert cf.vault.balance() - ethStartBalVault == -TEST_AMNT
    assert cf.ALICE.balance() - tokenStartBalRecipient == TEST_AMNT

    # Transferring out again should fail
    # No specific error message for failing eth transfer
    with reverts():
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, TEST_AMNT)
    
    # Fetch token deposit
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, JUNK_HEX, DepositToken, cleanHexStrPad(token.address))
    token.transfer(depositAddr, TEST_AMNT, {'from': cf.DEPLOYER})

    assert token.balanceOf(cf.vault) == 0

    callDataNoSig = cf.vault.fetchDepositToken.encode_input(NULL_SIG_DATA, JUNK_HEX, token)
    cf.vault.fetchDepositToken(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX, token)
    
    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == TEST_AMNT

    # Transfer half the tokens in the vault
    amount = TEST_AMNT/2
    tokenStartBalVault = token.balanceOf(cf.vault)
    tokenStartBalRecipient = token.balanceOf(cf.ALICE)

    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, token, cf.ALICE, amount)
    cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), token, cf.ALICE, amount)
    
    assert token.balanceOf(cf.vault) - tokenStartBalVault == -amount
    assert token.balanceOf(cf.ALICE) - tokenStartBalRecipient == amount


def test_fetchDepositEthBatch_transfer_fetchDepositTokenBatch_transfer(cf, token, DepositEth, DepositToken):
    # Get the address to deposit to and deposit
    swapIDs = [cleanHexStrPad(0), cleanHexStrPad(1)]
    depositAddr = getCreate2Addr(cf.vault.address, swapIDs[0], DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)
    depositAddr2 = getCreate2Addr(cf.vault.address, swapIDs[1], DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr2, 2 * TEST_AMNT)

    assert cf.vault.balance() == 0

    callDataNoSig = cf.vault.fetchDepositEthBatch.encode_input(NULL_SIG_DATA, swapIDs)
    cf.vault.fetchDepositEthBatch(AGG_SIGNER_1.getSigData(callDataNoSig), swapIDs)

    assert web3.eth.getBalance(web3.toChecksumAddress(depositAddr)) == 0
    assert web3.eth.getBalance(web3.toChecksumAddress(depositAddr2)) == 0
    assert cf.vault.balance() == 3 * TEST_AMNT

    # Transfer the eth out the vault
    ethStartBalVault = cf.vault.balance()
    tokenStartBalRecipient = cf.ALICE.balance()

    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, cf.ALICE, TEST_AMNT)
    cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, TEST_AMNT)
    
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
    cf.vault.fetchDepositTokenBatch(AGG_SIGNER_1.getSigData(callDataNoSig), swapIDs, [token, token])
    
    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == 3 * TEST_AMNT

    # Transfer half the tokens in the vault
    amount = TEST_AMNT * 1.5
    tokenStartBalVault = token.balanceOf(cf.vault)
    tokenStartBalRecipient = token.balanceOf(cf.ALICE)

    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, token, cf.ALICE, amount)
    cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), token, cf.ALICE, amount)
    
    assert token.balanceOf(cf.vault) - tokenStartBalVault == -amount
    assert token.balanceOf(cf.ALICE) - tokenStartBalRecipient == amount