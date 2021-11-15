from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy
from utils import *
from random import choices

@given(
    fetchAmounts=strategy('uint[]', max_value=TEST_AMNT, max_length=int(INIT_TOKEN_SUPPLY / TEST_AMNT)),
    fetchSwapIDs=strategy('bytes32[]', unique=True),
    tranRecipients=strategy('address[]', unique=True),
    tranAmounts=strategy('uint[]', max_value=TEST_AMNT),
    sender=strategy('address')
)
def test_setAggKeyByAggKey_allBatch(cfAW, token, token2, DepositToken, DepositEth, fetchAmounts, fetchSwapIDs, tranRecipients, tranAmounts, sender):

    # Allowing this breaks the refund test
    if sender in tranRecipients: return

    # Change agg keys
    setAggKeyWithAggKey_test(cfAW)

    # Sort out deposits first so enough can be sent to the create2 addresses
    fetchMinLen = trimToShortest([fetchAmounts, fetchSwapIDs])
    tokensList = [ETH_ADDR, token, token2]
    fetchTokens = choices(tokensList, k=fetchMinLen)

    fetchTotals = {tok: sum([fetchAmounts[i] for i, x in enumerate(fetchTokens) if x == tok]) for tok in tokensList}

    # Transfer tokens to the deposit addresses
    for am, id, tok in zip(fetchAmounts, fetchSwapIDs, fetchTokens):
        # Get the address to deposit to and deposit
        if tok == ETH_ADDR:
            depositAddr = getCreate2Addr(cfAW.vault.address, id.hex(), DepositEth, "")
            cfAW.DEPLOYER.transfer(depositAddr, am)
        else:
            depositAddr = getCreate2Addr(cfAW.vault.address, id.hex(), DepositToken, cleanHexStrPad(tok.address))
            tok.transfer(depositAddr, am, {'from': cfAW.DEPLOYER})

    # Commented out this assertion as the setAggKeyWithAggKey_test function above
    # will cause a refund to the caller, which will decrease vault's balance
    # assert cfAW.vault.balance() == ONE_ETH
    assert token.balanceOf(cfAW.vault) == 0
    assert token2.balanceOf(cfAW.vault) == 0

    # Transfers
    tranMinLen = trimToShortest([tranRecipients, tranAmounts])
    tranTokens = choices(tokensList, k=tranMinLen)

    tranTotals = {tok: sum([tranAmounts[i] for i, x in enumerate(tranTokens) if x == tok]) for tok in tokensList}
    validEthIdxs = getValidTranIdxs(tranTokens, tranAmounts, fetchTotals[ETH_ADDR] + ONE_ETH, ETH_ADDR)
    tranTotals[ETH_ADDR] = sum([tranAmounts[i] for i, x in enumerate(tranTokens) if x == ETH_ADDR and i in validEthIdxs])

    ethStartBalVault = cfAW.vault.balance()
    ethBals = [web3.eth.get_balance(str(recip)) for recip in tranRecipients]
    tokenBals = [token.balanceOf(recip) for recip in tranRecipients]
    token2Bals = [token2.balanceOf(recip) for recip in tranRecipients]

    callDataNoSig = cfAW.vault.allBatch.encode_input(agg_null_sig(cfAW.keyManager.address, chain.id), fetchSwapIDs, fetchTokens, tranTokens, tranRecipients, tranAmounts)

    # Check allBatch fails with the old agg key
    with reverts(REV_MSG_SIG):
        cfAW.vault.allBatch(AGG_SIGNER_1.getSigData(callDataNoSig, cfAW.keyManager.address), fetchSwapIDs, fetchTokens, tranTokens, tranRecipients, tranAmounts, {'from': sender})

    callDataNoSig = cfAW.vault.allBatch.encode_input(agg_null_sig(cfAW.keyManager.address, chain.id), fetchSwapIDs, fetchTokens, tranTokens, tranRecipients, tranAmounts)

    # If it tries to transfer an amount of tokens out the vault that is more than it fetched, it'll revert
    if any([tranTotals[tok] > fetchTotals[tok] for tok in tokensList[1:]]):
        with reverts():
            cfAW.vault.allBatch(AGG_SIGNER_2.getSigData(callDataNoSig, cfAW.keyManager.address), fetchSwapIDs, fetchTokens, tranTokens, tranRecipients, tranAmounts, {'from': sender})
    else:
        balanceBefore = sender.balance()
        tx = cfAW.vault.allBatch(AGG_SIGNER_2.getSigData(callDataNoSig, cfAW.keyManager.address), fetchSwapIDs, fetchTokens, tranTokens, tranRecipients, tranAmounts, {'from': sender})
        balanceAfter = sender.balance()
        refund = txRefundTest(balanceBefore, balanceAfter, tx)

        assert cfAW.vault.balance() == ethStartBalVault + (fetchTotals[ETH_ADDR] - tranTotals[ETH_ADDR]) - refund
        assert token.balanceOf(cfAW.vault) == fetchTotals[token] - tranTotals[token]
        assert token2.balanceOf(cfAW.vault) == fetchTotals[token2] - tranTotals[token2]

        for i in range(len(tranRecipients)):
            if tranTokens[i] == ETH_ADDR:
                if i in validEthIdxs: assert web3.eth.get_balance(str(tranRecipients[i])) == ethBals[i] + tranAmounts[i]
            elif tranTokens[i] == token:
                assert token.balanceOf(tranRecipients[i]) == tokenBals[i] + tranAmounts[i]
            elif tranTokens[i] == token2:
                assert token2.balanceOf(tranRecipients[i]) == token2Bals[i] + tranAmounts[i]
            else:
                assert False, "Panic"