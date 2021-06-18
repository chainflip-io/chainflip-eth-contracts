from consts import *
from brownie import reverts


def test_fetchDepositEth_transfer_fetchDepositToken_transfer(cf, token, DepositEth, DepositToken):
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, JUNK_HEX_PAD, DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)

    assert cf.vault.balance() == 0

    callDataNoSig = cf.vault.fetchDepositEth.encode_input(agg_null_sig(), JUNK_HEX_PAD)
    cf.vault.fetchDepositEth(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX_PAD)

    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
    assert cf.vault.balance() == TEST_AMNT

    # Transfer the eth out the vault
    ethStartBalVault = cf.vault.balance()
    tokenStartBalRecipient = cf.ALICE.balance()

    callDataNoSig = cf.vault.transfer.encode_input(agg_null_sig(), ETH_ADDR, cf.ALICE, TEST_AMNT)
    cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, TEST_AMNT)
    
    assert cf.vault.balance() - ethStartBalVault == -TEST_AMNT
    assert cf.ALICE.balance() - tokenStartBalRecipient == TEST_AMNT

    # Transferring out again should fail
    # No specific error message for failing eth transfer
    with reverts():
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, TEST_AMNT)
    
    # Fetch token deposit
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, JUNK_HEX_PAD, DepositToken, cleanHexStrPad(token.address))
    token.transfer(depositAddr, TEST_AMNT, {'from': cf.DEPLOYER})

    assert token.balanceOf(cf.vault) == 0

    callDataNoSig = cf.vault.fetchDepositToken.encode_input(agg_null_sig(), JUNK_HEX_PAD, token)
    cf.vault.fetchDepositToken(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX_PAD, token)
    
    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == TEST_AMNT

    # Transfer half the tokens out the vault
    amount = TEST_AMNT/2
    tokenStartBalVault = token.balanceOf(cf.vault)
    tokenStartBalRecipient = token.balanceOf(cf.ALICE)

    callDataNoSig = cf.vault.transfer.encode_input(agg_null_sig(), token, cf.ALICE, amount)
    cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), token, cf.ALICE, amount)
    
    assert token.balanceOf(cf.vault) - tokenStartBalVault == -amount
    assert token.balanceOf(cf.ALICE) - tokenStartBalRecipient == amount


def test_fetchDepositEthBatch_transfer_fetchDepositTokenBatch_transfer(cf, token, DepositEth, DepositToken):
    swapIDs = [cleanHexStrPad(0), cleanHexStrPad(1)]
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, swapIDs[0], DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)
    depositAddr2 = getCreate2Addr(cf.vault.address, swapIDs[1], DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr2, 2 * TEST_AMNT)

    assert cf.vault.balance() == 0

    callDataNoSig = cf.vault.fetchDepositEthBatch.encode_input(agg_null_sig(), swapIDs)
    cf.vault.fetchDepositEthBatch(AGG_SIGNER_1.getSigData(callDataNoSig), swapIDs)

    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr2)) == 0
    assert cf.vault.balance() == 3 * TEST_AMNT

    # Transfer the eth out the vault
    ethStartBalVault = cf.vault.balance()
    ethStartBalRecipient = cf.ALICE.balance()

    callDataNoSig = cf.vault.transfer.encode_input(agg_null_sig(), ETH_ADDR, cf.ALICE, TEST_AMNT)
    cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, TEST_AMNT)
    
    assert cf.vault.balance() - ethStartBalVault == -TEST_AMNT
    assert cf.ALICE.balance() - ethStartBalRecipient == TEST_AMNT

    # Transferring out again should fail
    # No specific error message for failing eth transfer
    with reverts():
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, (2 * TEST_AMNT) + 1)
    
    # Fetch token deposit
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, swapIDs[0], DepositToken, cleanHexStrPad(token.address))
    token.transfer(depositAddr, TEST_AMNT, {'from': cf.DEPLOYER})
    depositAddr2 = getCreate2Addr(cf.vault.address, swapIDs[1], DepositToken, cleanHexStrPad(token.address))
    token.transfer(depositAddr2, 2 * TEST_AMNT, {'from': cf.DEPLOYER})

    assert token.balanceOf(cf.vault) == 0

    callDataNoSig = cf.vault.fetchDepositTokenBatch.encode_input(agg_null_sig(), swapIDs, [token, token])
    cf.vault.fetchDepositTokenBatch(AGG_SIGNER_1.getSigData(callDataNoSig), swapIDs, [token, token])
    
    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == 3 * TEST_AMNT

    # Transfer half the tokens out the vault
    amount = TEST_AMNT * 1.5
    tokenStartBalVault = token.balanceOf(cf.vault)
    tokenStartBalRecipient = token.balanceOf(cf.ALICE)

    callDataNoSig = cf.vault.transfer.encode_input(agg_null_sig(), token, cf.ALICE, amount)
    cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), token, cf.ALICE, amount)
    
    assert token.balanceOf(cf.vault) - tokenStartBalVault == -amount
    assert token.balanceOf(cf.ALICE) - tokenStartBalRecipient == amount


def test_fetchDepositTokenBatch_transferBatch_fetchDepositEthBatch_transferBatch(cf, token, DepositEth, DepositToken):
    swapIDs = [cleanHexStrPad(0), cleanHexStrPad(1)]
    # Fetch token deposit
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, swapIDs[0], DepositToken, cleanHexStrPad(token.address))
    token.transfer(depositAddr, TEST_AMNT, {'from': cf.DEPLOYER})
    depositAddr2 = getCreate2Addr(cf.vault.address, swapIDs[1], DepositToken, cleanHexStrPad(token.address))
    token.transfer(depositAddr2, 2 * TEST_AMNT, {'from': cf.DEPLOYER})

    assert token.balanceOf(cf.vault) == 0

    callDataNoSig = cf.vault.fetchDepositTokenBatch.encode_input(agg_null_sig(), swapIDs, [token, token])
    cf.vault.fetchDepositTokenBatch(AGG_SIGNER_1.getSigData(callDataNoSig), swapIDs, [token, token])
    
    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == 3 * TEST_AMNT

    # Transfer most of the tokens out the vault
    amountAlice = TEST_AMNT * 1.5
    amountBob = int(TEST_AMNT * 0.5)
    tokenStartBalVault = token.balanceOf(cf.vault)
    tokenStartBalAlice = token.balanceOf(cf.ALICE)
    tokenStartBalBob = token.balanceOf(cf.BOB)

    callDataNoSig = cf.vault.transferBatch.encode_input(agg_null_sig(), [token, token], [cf.ALICE, cf.BOB], [amountAlice, amountBob])
    cf.vault.transferBatch(AGG_SIGNER_1.getSigData(callDataNoSig), [token, token], [cf.ALICE, cf.BOB], [amountAlice, amountBob])
    
    assert token.balanceOf(cf.vault) - tokenStartBalVault == - amountAlice - amountBob
    assert token.balanceOf(cf.ALICE) - tokenStartBalAlice == amountAlice
    assert token.balanceOf(cf.BOB) - tokenStartBalBob == amountBob

    # Transferring out again should fail
    callDataNoSig = cf.vault.transferBatch.encode_input(agg_null_sig(), [token, token], [cf.ALICE, cf.BOB], [amountAlice, amountBob])
    with reverts(REV_MSG_ERC20_EXCEED_BAL):
        cf.vault.transferBatch(AGG_SIGNER_1.getSigData(callDataNoSig), [token, token], [cf.ALICE, cf.BOB], [amountAlice, amountBob])
    
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, swapIDs[0], DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)
    depositAddr2 = getCreate2Addr(cf.vault.address, swapIDs[1], DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr2, 2 * TEST_AMNT)

    assert cf.vault.balance() == 0

    callDataNoSig = cf.vault.fetchDepositEthBatch.encode_input(agg_null_sig(), swapIDs)
    cf.vault.fetchDepositEthBatch(AGG_SIGNER_1.getSigData(callDataNoSig), swapIDs)

    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr2)) == 0
    assert cf.vault.balance() == 3 * TEST_AMNT

    # Transfer the eth out the vault
    amountAlice = TEST_AMNT * 1.5
    amountBob = int(TEST_AMNT * 0.5)
    ethStartBalVault = cf.vault.balance()
    ethStartBalAlice = cf.ALICE.balance()
    ethStartBalBob = cf.BOB.balance()

    callDataNoSig = cf.vault.transferBatch.encode_input(agg_null_sig(), [ETH_ADDR, ETH_ADDR], [cf.ALICE, cf.BOB], [amountAlice, amountBob])
    cf.vault.transferBatch(AGG_SIGNER_1.getSigData(callDataNoSig), [ETH_ADDR, ETH_ADDR], [cf.ALICE, cf.BOB], [amountAlice, amountBob])
    
    assert cf.vault.balance() - ethStartBalVault == - amountAlice - amountBob
    assert cf.ALICE.balance() - ethStartBalAlice == amountAlice
    assert cf.BOB.balance() - ethStartBalBob == amountBob


def test_fetchDepositTokenBatch_transferBatch_allBatch(cf, token, DepositEth, DepositToken):
    swapIDs = [cleanHexStrPad(0), cleanHexStrPad(1)]
    # Fetch token deposit
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, swapIDs[0], DepositToken, cleanHexStrPad(token.address))
    token.transfer(depositAddr, TEST_AMNT, {'from': cf.DEPLOYER})
    depositAddr2 = getCreate2Addr(cf.vault.address, swapIDs[1], DepositToken, cleanHexStrPad(token.address))
    token.transfer(depositAddr2, 2 * TEST_AMNT, {'from': cf.DEPLOYER})

    assert token.balanceOf(cf.vault) == 0

    callDataNoSig = cf.vault.fetchDepositTokenBatch.encode_input(agg_null_sig(), swapIDs, [token, token])
    cf.vault.fetchDepositTokenBatch(AGG_SIGNER_1.getSigData(callDataNoSig), swapIDs, [token, token])
    
    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == 3 * TEST_AMNT

    # Transfer most of the tokens out the vault
    amountAlice = TEST_AMNT * 1.5
    amountBob = int(TEST_AMNT * 0.5)
    tokenStartBalVault = token.balanceOf(cf.vault)
    tokenStartBalAlice = token.balanceOf(cf.ALICE)
    tokenStartBalBob = token.balanceOf(cf.BOB)

    callDataNoSig = cf.vault.transferBatch.encode_input(agg_null_sig(), [token, token], [cf.ALICE, cf.BOB], [amountAlice, amountBob])
    cf.vault.transferBatch(AGG_SIGNER_1.getSigData(callDataNoSig), [token, token], [cf.ALICE, cf.BOB], [amountAlice, amountBob])
    
    assert token.balanceOf(cf.vault) - tokenStartBalVault == - amountAlice - amountBob
    assert token.balanceOf(cf.ALICE) - tokenStartBalAlice == amountAlice
    assert token.balanceOf(cf.BOB) - tokenStartBalBob == amountBob

    # Transferring out again should fail
    callDataNoSig = cf.vault.transferBatch.encode_input(agg_null_sig(), [token, token], [cf.ALICE, cf.BOB], [amountAlice, amountBob])
    with reverts(REV_MSG_ERC20_EXCEED_BAL):
        cf.vault.transferBatch(AGG_SIGNER_1.getSigData(callDataNoSig), [token, token], [cf.ALICE, cf.BOB], [amountAlice, amountBob])
    
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, swapIDs[0], DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)
    depositAddr2 = getCreate2Addr(cf.vault.address, swapIDs[1], DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr2, 2 * TEST_AMNT)

    assert cf.vault.balance() == 0

    # Eth bals
    amountEthAlice = TEST_AMNT * 1.5
    amountEthBob = int(TEST_AMNT * 0.5)
    ethStartBalVault = cf.vault.balance()
    ethStartBalAlice = cf.ALICE.balance()
    ethStartBalBob = cf.BOB.balance()

    # Token bals
    amountTokenBob = int(TEST_AMNT * 0.25)
    tokenStartBalVault = token.balanceOf(cf.vault)
    tokenStartBalBob = token.balanceOf(cf.BOB)


    callDataNoSig = cf.vault.allBatch.encode_input(
        agg_null_sig(),
        swapIDs,
        [ETH_ADDR, ETH_ADDR],
        [ETH_ADDR, ETH_ADDR, token],
        [cf.ALICE, cf.BOB, cf.BOB],
        [amountEthAlice, amountEthBob, amountTokenBob]
    )
    cf.vault.allBatch(
        AGG_SIGNER_1.getSigData(callDataNoSig),
        swapIDs,
        [ETH_ADDR, ETH_ADDR],
        [ETH_ADDR, ETH_ADDR, token],
        [cf.ALICE, cf.BOB, cf.BOB],
        [amountEthAlice, amountEthBob, amountTokenBob]
    )

    # Eth bals
    assert cf.vault.balance() - ethStartBalVault == 3 * TEST_AMNT - amountEthAlice - amountEthBob
    assert cf.ALICE.balance() - ethStartBalAlice == amountEthAlice
    assert cf.BOB.balance() - ethStartBalBob == amountEthBob

    # Token bals
    assert token.balanceOf(cf.vault) - tokenStartBalVault == -amountTokenBob
    assert token.balanceOf(cf.BOB) - tokenStartBalBob == amountTokenBob