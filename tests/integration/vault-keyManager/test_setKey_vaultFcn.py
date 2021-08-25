from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy
from utils import *
from random import choices


# # Test changing keys and then calling other fcns

# def test_setAggKeyByAggKey_transfer(cf):
#     # Change agg keys
#     setAggKeyWithAggKey_test(cf)

#     # Set up the transfer
#     cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)
#     startBalVault = cf.vault.balance()
#     startBalRecipient = cf.ALICE.balance()

#     # Check transfer fails with old agg key
#     callDataNoSig = cf.vault.transfer.encode_input(agg_null_sig(), ETH_ADDR, cf.ALICE, TEST_AMNT)
#     with reverts(REV_MSG_SIG):
#         cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, TEST_AMNT)

#     # Check transfer with new agg key
#     callDataNoSig = cf.vault.transfer.encode_input(agg_null_sig(), ETH_ADDR, cf.ALICE, TEST_AMNT)
#     tx = cf.vault.transfer(AGG_SIGNER_2.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, TEST_AMNT)

#     assert cf.vault.balance() - startBalVault == -TEST_AMNT
#     assert cf.ALICE.balance() - startBalRecipient == TEST_AMNT
#     txTimeTest(cf.keyManager.getLastValidateTime(), tx)


# def test_setAggKeyByAggKey_fetchDepositEth_transfer(cf, DepositEth):
#     recipient = cf.BOB
#     recipientStartBal = cf.BOB.balance()

#     # Change agg keys
#     setAggKeyWithAggKey_test(cf)

#     assert cf.BOB.balance() == recipientStartBal
#     assert cf.vault.balance() == 0

#     # Set up the deposit
#     depositAddr = getCreate2Addr(cf.vault.address, JUNK_HEX_PAD, DepositEth, "")
#     cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)

#     # Check transfer fails with old agg key
#     callDataNoSig = cf.vault.fetchDepositEth.encode_input(agg_null_sig(), JUNK_HEX_PAD)
#     with reverts(REV_MSG_SIG):
#         cf.vault.fetchDepositEth(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX_PAD)

#     # Fetch the deposit with new agg key
#     callDataNoSig = cf.vault.fetchDepositEth.encode_input(agg_null_sig(), JUNK_HEX_PAD)
#     tx = cf.vault.fetchDepositEth(AGG_SIGNER_2.getSigData(callDataNoSig), JUNK_HEX_PAD)

#     assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
#     assert cf.vault.balance() == TEST_AMNT
#     assert cf.BOB.balance() == recipientStartBal
#     txTimeTest(cf.keyManager.getLastValidateTime(), tx)

#     # Check transfer fails with old agg key
#     callDataNoSig = cf.vault.transfer.encode_input(agg_null_sig(), ETH_ADDR, recipient, TEST_AMNT)
#     with reverts(REV_MSG_SIG):
#         cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, recipient, TEST_AMNT)

#     callDataNoSig = cf.vault.transfer.encode_input(agg_null_sig(), ETH_ADDR, recipient, TEST_AMNT)
#     tx = cf.vault.transfer(AGG_SIGNER_2.getSigData(callDataNoSig), ETH_ADDR, recipient, TEST_AMNT)

#     assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
#     assert cf.vault.balance() == 0
#     assert cf.BOB.balance() == recipientStartBal + TEST_AMNT
#     txTimeTest(cf.keyManager.getLastValidateTime(), tx)


# def test_setAggKeyByAggKey_fetchDepositToken_transfer(cf, token, DepositToken):
#     recipient = cf.BOB
#     recipientStartBal = token.balanceOf(cf.BOB)

#     # Change agg keys
#     setAggKeyWithAggKey_test(cf)

#     assert token.balanceOf(cf.BOB) == recipientStartBal
#     assert token.balanceOf(cf.vault) == 0

#     # Set up the deposit
#     depositAddr = getCreate2Addr(cf.vault.address, JUNK_HEX_PAD, DepositToken, cleanHexStrPad(token.address))
#     token.transfer(depositAddr, TEST_AMNT, {'from': cf.DEPLOYER})

#     # Check transfer fails with old agg key
#     callDataNoSig = cf.vault.fetchDepositToken.encode_input(agg_null_sig(), JUNK_HEX_PAD, token)

#     with reverts(REV_MSG_SIG):
#         cf.vault.fetchDepositToken(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX_PAD, token)

#     # Fetch the deposit with new agg key
#     callDataNoSig = cf.vault.fetchDepositToken.encode_input(agg_null_sig(), JUNK_HEX_PAD, token)
#     tx = cf.vault.fetchDepositToken(AGG_SIGNER_2.getSigData(callDataNoSig), JUNK_HEX_PAD, token)

#     assert token.balanceOf(depositAddr) == 0
#     assert token.balanceOf(cf.vault) == TEST_AMNT
#     assert token.balanceOf(cf.BOB) == recipientStartBal
#     txTimeTest(cf.keyManager.getLastValidateTime(), tx)

#     # Check transfer fails with old agg key
#     callDataNoSig = cf.vault.transfer.encode_input(agg_null_sig(), token, recipient, TEST_AMNT)
#     with reverts(REV_MSG_SIG):
#         cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), token, recipient, TEST_AMNT)

#     # Transfer to recipient
#     callDataNoSig = cf.vault.transfer.encode_input(agg_null_sig(), token, recipient, TEST_AMNT)
#     tx = cf.vault.transfer(AGG_SIGNER_2.getSigData(callDataNoSig), token, recipient, TEST_AMNT)

#     assert token.balanceOf(depositAddr) == 0
#     assert token.balanceOf(cf.vault) == 0
#     assert token.balanceOf(cf.BOB) == recipientStartBal + TEST_AMNT
#     txTimeTest(cf.keyManager.getLastValidateTime(), tx)


# def test_setAggKeyByAggKey_fetchDepositEthBatch_transfer_fetchDepositBatchBatch_transfer(cf, token, DepositEth, DepositToken):
#     # Change agg keys
#     setAggKeyWithAggKey_test(cf)

#     # Get the address to deposit to and deposit
#     swapIDs = [cleanHexStrPad(0), cleanHexStrPad(1)]
#     depositAddr = getCreate2Addr(cf.vault.address, swapIDs[0], DepositEth, "")
#     cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)
#     depositAddr2 = getCreate2Addr(cf.vault.address, swapIDs[1], DepositEth, "")
#     cf.DEPLOYER.transfer(depositAddr2, 2 * TEST_AMNT)

#     assert cf.vault.balance() == 0

#     callDataNoSig = cf.vault.fetchDepositEthBatch.encode_input(agg_null_sig(), swapIDs)

#     # Check fetchDepositEthBatch fails with old agg key
#     with reverts(REV_MSG_SIG):
#         cf.vault.fetchDepositEthBatch(AGG_SIGNER_1.getSigData(callDataNoSig), swapIDs)

#     # Fetch the deposits with new agg key
#     callDataNoSig = cf.vault.fetchDepositEthBatch.encode_input(agg_null_sig(), swapIDs)
#     cf.vault.fetchDepositEthBatch(AGG_SIGNER_2.getSigData(callDataNoSig), swapIDs)

#     assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
#     assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr2)) == 0
#     assert cf.vault.balance() == 3 * TEST_AMNT

#     # Transfer the eth out the vault
#     ethStartBalVault = cf.vault.balance()
#     tokenStartBalRecipient = cf.ALICE.balance()

#     callDataNoSig = cf.vault.transfer.encode_input(agg_null_sig(), ETH_ADDR, cf.ALICE, TEST_AMNT)

#     # Check transfer fails with old agg key
#     with reverts(REV_MSG_SIG):
#         cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, TEST_AMNT)

#     # Transfer with new agg key
#     callDataNoSig = cf.vault.transfer.encode_input(agg_null_sig(), ETH_ADDR, cf.ALICE, TEST_AMNT)
#     cf.vault.transfer(AGG_SIGNER_2.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, TEST_AMNT)

#     assert cf.vault.balance() - ethStartBalVault == -TEST_AMNT
#     assert cf.ALICE.balance() - tokenStartBalRecipient == TEST_AMNT

#     # Transferring out again should fail
#     # No specific error message for failing eth transfer
#     with reverts():
#         cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, (2 * TEST_AMNT) + 1)

#     # Fetch token deposit
#     # Get the address to deposit to and deposit
#     depositAddr = getCreate2Addr(cf.vault.address, swapIDs[0], DepositToken, cleanHexStrPad(token.address))
#     token.transfer(depositAddr, TEST_AMNT, {'from': cf.DEPLOYER})
#     depositAddr2 = getCreate2Addr(cf.vault.address, swapIDs[1], DepositToken, cleanHexStrPad(token.address))
#     cf.DEPLOYER.transfer(depositAddr2, 2 * TEST_AMNT)
#     token.transfer(depositAddr2, 2 * TEST_AMNT, {'from': cf.DEPLOYER})

#     assert token.balanceOf(cf.vault) == 0

#     callDataNoSig = cf.vault.fetchDepositTokenBatch.encode_input(agg_null_sig(), swapIDs, [token, token])

#     # Check fetchDepositTokenBatch fails with old agg key
#     with reverts(REV_MSG_SIG):
#         cf.vault.fetchDepositTokenBatch(AGG_SIGNER_1.getSigData(callDataNoSig), swapIDs, [token, token])

#     # Fetch the deposits with new agg key
#     callDataNoSig = cf.vault.fetchDepositTokenBatch.encode_input(agg_null_sig(), swapIDs, [token, token])
#     cf.vault.fetchDepositTokenBatch(AGG_SIGNER_2.getSigData(callDataNoSig), swapIDs, [token, token])

#     assert token.balanceOf(depositAddr) == 0
#     assert token.balanceOf(cf.vault) == 3 * TEST_AMNT

#     # Transfer half the tokens in the vault
#     amount = TEST_AMNT * 1.5
#     tokenStartBalVault = token.balanceOf(cf.vault)
#     tokenStartBalRecipient = token.balanceOf(cf.ALICE)

#     callDataNoSig = cf.vault.transfer.encode_input(agg_null_sig(), token, cf.ALICE, amount)
#     # Check transfer fails with old agg key
#     with reverts(REV_MSG_SIG):
#         cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), token, cf.ALICE, amount)

#     callDataNoSig = cf.vault.transfer.encode_input(agg_null_sig(), token, cf.ALICE, amount)
#     cf.vault.transfer(AGG_SIGNER_2.getSigData(callDataNoSig), token, cf.ALICE, amount)

#     assert token.balanceOf(cf.vault) - tokenStartBalVault == -amount
#     assert token.balanceOf(cf.ALICE) - tokenStartBalRecipient == amount


# def test_fetchDepositEthBatch_setAggKeyByAggKey_transferBatch(cf, token, DepositEth):
#     # Get the address to deposit to and deposit
#     swapIDs = [cleanHexStrPad(0), cleanHexStrPad(1)]
#     depositAddr = getCreate2Addr(cf.vault.address, swapIDs[0], DepositEth, "")
#     cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)
#     depositAddr2 = getCreate2Addr(cf.vault.address, swapIDs[1], DepositEth, "")
#     cf.DEPLOYER.transfer(depositAddr2, 2 * TEST_AMNT)

#     assert cf.vault.balance() == 0

#     callDataNoSig = cf.vault.fetchDepositEthBatch.encode_input(agg_null_sig(), swapIDs)

#     # Check fetchDepositEthBatch fails with the future agg key
#     with reverts(REV_MSG_SIG):
#         cf.vault.fetchDepositEthBatch(AGG_SIGNER_2.getSigData(callDataNoSig), swapIDs)

#     # Fetch the deposits with new agg key
#     callDataNoSig = cf.vault.fetchDepositEthBatch.encode_input(agg_null_sig(), swapIDs)
#     cf.vault.fetchDepositEthBatch(AGG_SIGNER_1.getSigData(callDataNoSig), swapIDs)

#     assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
#     assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr2)) == 0
#     assert cf.vault.balance() == 3 * TEST_AMNT

#     # Change agg keys
#     setAggKeyWithAggKey_test(cf)

#     # Transfer the eth out the vault
#     amountAlice = TEST_AMNT * 1.5
#     amountBob = int(TEST_AMNT * 0.5)
#     ethStartBalVault = cf.vault.balance()
#     ethStartBalAlice = cf.ALICE.balance()
#     ethStartBalBob = cf.BOB.balance()

#     callDataNoSig = cf.vault.transferBatch.encode_input(agg_null_sig(), [ETH_ADDR, ETH_ADDR], [cf.ALICE, cf.BOB], [amountAlice, amountBob])

#     # Check fetchDepositEthBatch fails with the old agg key
#     with reverts(REV_MSG_SIG):
#         cf.vault.transferBatch(AGG_SIGNER_1.getSigData(callDataNoSig), [ETH_ADDR, ETH_ADDR], [cf.ALICE, cf.BOB], [amountAlice, amountBob])

#     callDataNoSig = cf.vault.transferBatch.encode_input(agg_null_sig(), [ETH_ADDR, ETH_ADDR], [cf.ALICE, cf.BOB], [amountAlice, amountBob])
#     cf.vault.transferBatch(AGG_SIGNER_2.getSigData(callDataNoSig), [ETH_ADDR, ETH_ADDR], [cf.ALICE, cf.BOB], [amountAlice, amountBob])

#     assert cf.vault.balance() - ethStartBalVault == - amountAlice - amountBob
#     assert cf.ALICE.balance() - ethStartBalAlice == amountAlice
#     assert cf.BOB.balance() - ethStartBalBob == amountBob


@given(
    fetchAmounts=strategy('uint[]', max_value=TEST_AMNT, max_length=int(INIT_TOKEN_SUPPLY / TEST_AMNT)),
    fetchSwapIDs=strategy('bytes32[]', unique=True),
    tranRecipients=strategy('address[]', unique=True),
    tranAmounts=strategy('uint[]', max_value=TEST_AMNT),
    sender=strategy('address')
)
def test_setAggKeyByAggKey_allBatch(cf, token, token2, DepositToken, DepositEth, fetchAmounts, fetchSwapIDs, tranRecipients, tranAmounts, sender):

    # Allowing this breaks the refund test
    if sender in tranRecipients: return

    # Change agg keys
    setAggKeyWithAggKey_test(cf)

    # Sort out deposits first so enough can be sent to the create2 addresses
    fetchMinLen = trimToShortest([fetchAmounts, fetchSwapIDs])
    tokensList = [ETH_ADDR, token, token2]
    fetchTokens = choices(tokensList, k=fetchMinLen)

    fetchTotals = {tok: sum([fetchAmounts[i] for i, x in enumerate(fetchTokens) if x == tok]) for tok in tokensList}

    # Transfer tokens to the deposit addresses
    for am, id, tok in zip(fetchAmounts, fetchSwapIDs, fetchTokens):
        # Get the address to deposit to and deposit
        if tok == ETH_ADDR:
            depositAddr = getCreate2Addr(cf.vault.address, id.hex(), DepositEth, "")
            cf.DEPLOYER.transfer(depositAddr, am)
        else:
            depositAddr = getCreate2Addr(cf.vault.address, id.hex(), DepositToken, cleanHexStrPad(tok.address))
            tok.transfer(depositAddr, am, {'from': cf.DEPLOYER})

    # Commented out this assertion as the setAggKeyWithAggKey_test function above
    # will cause a refund to the caller, which will decrease vault's balance
    # assert cf.vault.balance() == ONE_ETH
    assert token.balanceOf(cf.vault) == 0
    assert token2.balanceOf(cf.vault) == 0

    # Transfers
    tranMinLen = trimToShortest([tranRecipients, tranAmounts])
    tranTokens = choices(tokensList, k=tranMinLen)

    tranTotals = {tok: sum([tranAmounts[i] for i, x in enumerate(tranTokens) if x == tok]) for tok in tokensList}
    validEthIdxs = getValidTranIdxs(tranTokens, tranAmounts, fetchTotals[ETH_ADDR] + ONE_ETH, ETH_ADDR)
    tranTotals[ETH_ADDR] = sum([tranAmounts[i] for i, x in enumerate(tranTokens) if x == ETH_ADDR and i in validEthIdxs])

    ethStartBalVault = cf.vault.balance()
    ethBals = [web3.eth.get_balance(str(recip)) for recip in tranRecipients]
    tokenBals = [token.balanceOf(recip) for recip in tranRecipients]
    token2Bals = [token2.balanceOf(recip) for recip in tranRecipients]

    callDataNoSig = cf.vault.allBatch.encode_input(agg_null_sig(), fetchSwapIDs, fetchTokens, tranTokens, tranRecipients, tranAmounts)

    # Check allBatch fails with the old agg key
    with reverts(REV_MSG_SIG):
        cf.vault.allBatch(AGG_SIGNER_1.getSigData(callDataNoSig), fetchSwapIDs, fetchTokens, tranTokens, tranRecipients, tranAmounts, {'from': sender})

    callDataNoSig = cf.vault.allBatch.encode_input(agg_null_sig(), fetchSwapIDs, fetchTokens, tranTokens, tranRecipients, tranAmounts)

    # If it tries to transfer an amount of tokens out the vault that is more than it fetched, it'll revert
    if any([tranTotals[tok] > fetchTotals[tok] for tok in tokensList[1:]]):
        with reverts():
            cf.vault.allBatch(AGG_SIGNER_2.getSigData(callDataNoSig), fetchSwapIDs, fetchTokens, tranTokens, tranRecipients, tranAmounts, {'from': sender})
    else:
        balanceBefore = sender.balance()
        tx = cf.vault.allBatch(AGG_SIGNER_2.getSigData(callDataNoSig), fetchSwapIDs, fetchTokens, tranTokens, tranRecipients, tranAmounts, {'from': sender})
        balanceAfter = sender.balance()
        refund = txRefundTest(balanceBefore, balanceAfter, tx)

        assert cf.vault.balance() == ethStartBalVault + (fetchTotals[ETH_ADDR] - tranTotals[ETH_ADDR]) - refund
        assert token.balanceOf(cf.vault) == fetchTotals[token] - tranTotals[token]
        assert token2.balanceOf(cf.vault) == fetchTotals[token2] - tranTotals[token2]

        for i in range(len(tranRecipients)):
            if tranTokens[i] == ETH_ADDR:
                if i in validEthIdxs: assert web3.eth.get_balance(str(tranRecipients[i])) == ethBals[i] + tranAmounts[i]
            elif tranTokens[i] == token:
                assert token.balanceOf(tranRecipients[i]) == tokenBals[i] + tranAmounts[i]
            elif tranTokens[i] == token2:
                assert token2.balanceOf(tranRecipients[i]) == token2Bals[i] + tranAmounts[i]
            else:
                assert False, "Panic"