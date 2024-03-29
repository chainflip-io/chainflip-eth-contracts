from consts import *
from brownie import reverts, web3, history
from brownie.test import given, strategy
from random import choices
from utils import *
from shared_tests import *


@given(
    st_fetchAmounts=strategy(
        "uint[]", max_value=TEST_AMNT, max_length=int(INIT_TOKEN_SUPPLY / TEST_AMNT)
    ),
    st_fetchSwapIDs=strategy("bytes32[]", unique=True),
    st_tranRecipients=strategy("address[]", unique=True),
    st_tranAmounts=strategy("uint[]", max_value=TEST_AMNT),
    st_sender=strategy("address"),
)
def test_allBatch(
    cf,
    token,
    token2,
    Deposit,
    st_fetchAmounts,
    st_fetchSwapIDs,
    st_tranRecipients,
    st_tranAmounts,
    st_sender,
):
    # Sort out deposits first so enough can be sent to the create2 addresses
    fetchMinLen = trimToShortest([st_fetchAmounts, st_fetchSwapIDs])
    tokensList = [NATIVE_ADDR, token, token2]
    fetchTokens = choices(tokensList, k=fetchMinLen)
    fetchTotals = {
        tok: sum([st_fetchAmounts[i] for i, x in enumerate(fetchTokens) if x == tok])
        for tok in tokensList
    }
    depositAddrs = []
    # Transfer tokens to the deposit addresses
    for am, id, tok in zip(st_fetchAmounts, st_fetchSwapIDs, fetchTokens):
        # Get the address to deposit to and deposit
        if tok == NATIVE_ADDR:
            depositAddr = getCreate2Addr(
                cf.vault.address, id.hex(), Deposit, cleanHexStrPad(NATIVE_ADDR)
            )
            cf.SAFEKEEPER.transfer(depositAddr, am)
        else:
            depositAddr = getCreate2Addr(
                cf.vault.address, id.hex(), Deposit, cleanHexStrPad(tok.address)
            )
            tok.transfer(depositAddr, am, {"from": cf.SAFEKEEPER})
        depositAddrs.append(depositAddr)
    assert cf.vault.balance() == 0  # starting balance
    assert token.balanceOf(cf.vault) == 0
    assert token2.balanceOf(cf.vault) == 0

    # Transfers
    tranMinLen = trimToShortest([st_tranRecipients, st_tranAmounts])
    tranTokens = choices(tokensList, k=tranMinLen)

    tranTotals = {
        tok: sum([st_tranAmounts[i] for i, x in enumerate(tranTokens) if x == tok])
        for tok in tokensList
    }
    # Need to know which index that native transfers start to fail since they won't revert the tx, but won't send the expected amount
    cumulEthTran = 0
    validEthIdxs = []
    for i in range(len(tranTokens)):
        if tranTokens[i] == NATIVE_ADDR:
            if cumulEthTran + st_tranAmounts[i] <= fetchTotals[NATIVE_ADDR]:
                validEthIdxs.append(i)
                cumulEthTran += st_tranAmounts[i]
    tranTotals[NATIVE_ADDR] = sum(
        [
            st_tranAmounts[i]
            for i, x in enumerate(tranTokens)
            if x == NATIVE_ADDR and i in validEthIdxs
        ]
    )

    nativeBals = [web3.eth.get_balance(str(recip)) for recip in st_tranRecipients]
    tokenBals = [token.balanceOf(recip) for recip in st_tranRecipients]
    token2Bals = [token2.balanceOf(recip) for recip in st_tranRecipients]

    # Account for gas expenditure if st_sender is in transRecipients - storing initial transaction number
    if st_sender in st_tranRecipients:
        iniTransactionNumberst_sender = len(history.filter(sender=st_sender))

    deployFetchParams = craftDeployFetchParamsArray(st_fetchSwapIDs, fetchTokens)
    # Call fetch functions from recently deployed Deposit contracts (will fetch zero)
    fetchParamsArray = craftFetchParamsArray(depositAddrs, fetchTokens)
    transferParams = craftTransferParamsArray(
        tranTokens, st_tranRecipients, st_tranAmounts
    )
    args = (deployFetchParams, fetchParamsArray, transferParams)

    # If it tries to transfer an amount of tokens out the vault that is more than it fetched, it'll fail gracefully
    if any([tranTotals[tok] > fetchTotals[tok] for tok in tokensList[1:]]):
        tx = signed_call_cf(cf, cf.vault.allBatch, *args, sender=st_sender)
        # There might be multiple failures, so just check that there is at least one
        assert len(tx.events["TransferTokenFailed"]) >= 1

    else:
        signed_call_cf(cf, cf.vault.allBatch, *args, sender=st_sender)

        assert cf.vault.balance() == fetchTotals[NATIVE_ADDR] - tranTotals[NATIVE_ADDR]
        assert token.balanceOf(cf.vault) == fetchTotals[token] - tranTotals[token]
        assert token2.balanceOf(cf.vault) == fetchTotals[token2] - tranTotals[token2]

        for i in range(len(st_tranRecipients)):
            if tranTokens[i] == NATIVE_ADDR:
                if i in validEthIdxs:
                    finalEthBals = nativeBals[i] + st_tranAmounts[i]
                    # Account for gas expenditure if st_sender is in transRecipients
                    if st_tranRecipients[i] == st_sender:
                        finalEthBals -= calculateGasSpentByAddress(
                            st_tranRecipients[i], iniTransactionNumberst_sender
                        )
                    assert (
                        web3.eth.get_balance(str(st_tranRecipients[i])) == finalEthBals
                    )
            elif tranTokens[i] == token:
                assert (
                    token.balanceOf(st_tranRecipients[i])
                    == tokenBals[i] + st_tranAmounts[i]
                )
            elif tranTokens[i] == token2:
                assert (
                    token2.balanceOf(st_tranRecipients[i])
                    == token2Bals[i] + st_tranAmounts[i]
                )
            else:
                assert False, "Panic"


def test_allBatch_rev_sig(cf):
    deployFetchParams = [[JUNK_HEX_PAD, NATIVE_ADDR]]
    fetchParamsArray = [[NON_ZERO_ADDR, NATIVE_ADDR]]
    transferParams = [[NATIVE_ADDR, cf.ALICE, TEST_AMNT]]
    args = (deployFetchParams, fetchParamsArray, transferParams)

    sigData = AGG_SIGNER_1.getSigDataWithNonces(
        cf.keyManager, cf.vault.allBatch, nonces, *args
    )

    sigData_modif = sigData[:]
    sigData_modif[0] += 1
    with reverts(REV_MSG_SIG):
        cf.vault.allBatch(sigData_modif, *args, {"from": cf.ALICE})

    sigData_modif = sigData[:]
    sigData_modif[1] += 1
    with reverts(REV_MSG_SIG):
        cf.vault.allBatch(sigData_modif, *args, {"from": cf.ALICE})

    sigData_modif = sigData[:]
    sigData_modif[2] = NON_ZERO_ADDR
    with reverts(REV_MSG_SIG):
        cf.vault.allBatch(sigData_modif, *args, {"from": cf.ALICE})


def test_allBatch_rev_deploy(cf):
    deployFetchParams = [[JUNK_HEX_PAD, NATIVE_ADDR], [JUNK_HEX_PAD, NATIVE_ADDR]]
    fetchParamsArray = [[NON_ZERO_ADDR, NATIVE_ADDR]]
    transferParams = [[NATIVE_ADDR, cf.ALICE, TEST_AMNT]]
    args = (deployFetchParams, fetchParamsArray, transferParams)

    with reverts():
        signed_call_cf(cf, cf.vault.allBatch, *args)


def test_allBatch_rev_fetch(cf, Deposit):
    deployFetchParams = [[JUNK_HEX_PAD, NATIVE_ADDR]]
    # Use a non-used salt to get a different address
    depositAddr = getCreate2Addr(
        cf.vault.address,
        cleanHexStrPad(web3.toHex(1)),
        Deposit,
        cleanHexStrPad(NATIVE_ADDR),
    )
    fetchParamsArray = [[depositAddr, NON_ZERO_ADDR]]
    transferParams = [[NATIVE_ADDR, cf.ALICE, TEST_AMNT]]
    args = (deployFetchParams, fetchParamsArray, transferParams)

    with reverts():
        signed_call_cf(cf, cf.vault.allBatch, *args)


## Test allBatchV2


@given(
    st_fetchAmounts=strategy(
        "uint[]", max_value=TEST_AMNT, max_length=int(INIT_TOKEN_SUPPLY / TEST_AMNT)
    ),
    st_fetchSwapIDs=strategy("bytes32[]", unique=True),
    st_tranRecipients=strategy("address[]", unique=True),
    st_tranAmounts=strategy("uint[]", max_value=TEST_AMNT),
    st_sender=strategy("address"),
)
def test_allBatchV2(
    cf,
    token,
    token2,
    Deposit,
    st_fetchAmounts,
    st_fetchSwapIDs,
    st_tranRecipients,
    st_tranAmounts,
    st_sender,
):
    # Sort out deposits first so enough can be sent to the create2 addresses
    fetchMinLen = trimToShortest([st_fetchAmounts, st_fetchSwapIDs])
    tokensList = [NATIVE_ADDR, token, token2]
    fetchTokens = choices(tokensList, k=fetchMinLen)
    fetchTotals = {
        tok: sum([st_fetchAmounts[i] for i, x in enumerate(fetchTokens) if x == tok])
        for tok in tokensList
    }
    depositAddrs = []
    # Transfer tokens to the deposit addresses
    for am, id, tok in zip(st_fetchAmounts, st_fetchSwapIDs, fetchTokens):
        # Get the address to deposit to and deposit
        if tok == NATIVE_ADDR:
            depositAddr = getCreate2Addr(
                cf.vault.address, id.hex(), Deposit, cleanHexStrPad(NATIVE_ADDR)
            )
            cf.SAFEKEEPER.transfer(depositAddr, am)
        else:
            depositAddr = getCreate2Addr(
                cf.vault.address, id.hex(), Deposit, cleanHexStrPad(tok.address)
            )
            tok.transfer(depositAddr, am, {"from": cf.SAFEKEEPER})
        depositAddrs.append(depositAddr)
    assert cf.vault.balance() == 0  # starting balance
    assert token.balanceOf(cf.vault) == 0
    assert token2.balanceOf(cf.vault) == 0

    # Transfers
    tranMinLen = trimToShortest([st_tranRecipients, st_tranAmounts])
    tranTokens = choices(tokensList, k=tranMinLen)

    tranTotals = {
        tok: sum([st_tranAmounts[i] for i, x in enumerate(tranTokens) if x == tok])
        for tok in tokensList
    }
    # Need to know which index that native transfers start to fail since they won't revert the tx, but won't send the expected amount
    cumulEthTran = 0
    validEthIdxs = []
    for i in range(len(tranTokens)):
        if tranTokens[i] == NATIVE_ADDR:
            if cumulEthTran + st_tranAmounts[i] <= fetchTotals[NATIVE_ADDR]:
                validEthIdxs.append(i)
                cumulEthTran += st_tranAmounts[i]
    tranTotals[NATIVE_ADDR] = sum(
        [
            st_tranAmounts[i]
            for i, x in enumerate(tranTokens)
            if x == NATIVE_ADDR and i in validEthIdxs
        ]
    )

    nativeBals = [web3.eth.get_balance(str(recip)) for recip in st_tranRecipients]
    tokenBals = [token.balanceOf(recip) for recip in st_tranRecipients]
    token2Bals = [token2.balanceOf(recip) for recip in st_tranRecipients]

    # Account for gas expenditure if st_sender is in transRecipients - storing initial transaction number
    if st_sender in st_tranRecipients:
        iniTransactionNumberst_sender = len(history.filter(sender=st_sender))

    deployFetchParams = craftDeployFetchParamsArray(st_fetchSwapIDs, fetchTokens)
    # Call fetch functions from recently deployed Deposit contracts (will fetch zero)
    fetchParamsArray = craftFetchParamsArray(depositAddrs, fetchTokens)
    transferParams = craftTransferParamsArray(
        tranTokens, st_tranRecipients, st_tranAmounts
    )
    args = (fetchParamsArray, transferParams)

    # DeployAndFetch from deposit addresses
    signed_call_cf(
        cf, cf.vault.deployAndFetchBatch, deployFetchParams, sender=st_sender
    )

    # If it tries to transfer an amount of tokens out the vault that is more than it fetched, it'll fail gracefully
    if any([tranTotals[tok] > fetchTotals[tok] for tok in tokensList[1:]]):
        tx = signed_call_cf(cf, cf.vault.allBatchV2, *args, sender=st_sender)
        # There might be multiple failures, so just check that there is at least one
        assert len(tx.events["TransferTokenFailed"]) >= 1

    else:
        signed_call_cf(cf, cf.vault.allBatchV2, *args, sender=st_sender)

        assert cf.vault.balance() == fetchTotals[NATIVE_ADDR] - tranTotals[NATIVE_ADDR]
        assert token.balanceOf(cf.vault) == fetchTotals[token] - tranTotals[token]
        assert token2.balanceOf(cf.vault) == fetchTotals[token2] - tranTotals[token2]

        for i in range(len(st_tranRecipients)):
            if tranTokens[i] == NATIVE_ADDR:
                if i in validEthIdxs:
                    finalEthBals = nativeBals[i] + st_tranAmounts[i]
                    # Account for gas expenditure if st_sender is in transRecipients
                    if st_tranRecipients[i] == st_sender:
                        finalEthBals -= calculateGasSpentByAddress(
                            st_tranRecipients[i], iniTransactionNumberst_sender
                        )
                    assert (
                        web3.eth.get_balance(str(st_tranRecipients[i])) == finalEthBals
                    )
            elif tranTokens[i] == token:
                assert (
                    token.balanceOf(st_tranRecipients[i])
                    == tokenBals[i] + st_tranAmounts[i]
                )
            elif tranTokens[i] == token2:
                assert (
                    token2.balanceOf(st_tranRecipients[i])
                    == token2Bals[i] + st_tranAmounts[i]
                )
            else:
                assert False, "Panic"


def test_allBatchV2_rev_sig(cf):
    fetchParamsArray = [[NON_ZERO_ADDR, NATIVE_ADDR]]
    transferParams = [[NATIVE_ADDR, cf.ALICE, TEST_AMNT]]
    args = (fetchParamsArray, transferParams)

    sigData = AGG_SIGNER_1.getSigDataWithNonces(
        cf.keyManager, cf.vault.allBatchV2, nonces, *args
    )

    sigData_modif = sigData[:]
    sigData_modif[0] += 1
    with reverts(REV_MSG_SIG):
        cf.vault.allBatchV2(sigData_modif, *args, {"from": cf.ALICE})

    sigData_modif = sigData[:]
    sigData_modif[1] += 1
    with reverts(REV_MSG_SIG):
        cf.vault.allBatchV2(sigData_modif, *args, {"from": cf.ALICE})

    sigData_modif = sigData[:]
    sigData_modif[2] = NON_ZERO_ADDR
    with reverts(REV_MSG_SIG):
        cf.vault.allBatchV2(sigData_modif, *args, {"from": cf.ALICE})


def test_allBatchV2_rev_deploy(cf):
    fetchParamsArray = [[NON_ZERO_ADDR, NATIVE_ADDR]]
    transferParams = [[NATIVE_ADDR, cf.ALICE, TEST_AMNT]]
    args = (fetchParamsArray, transferParams)

    with reverts():
        signed_call_cf(cf, cf.vault.allBatchV2, *args)


def test_allBatchV2_rev_fetch(cf, Deposit):
    deployFetchParams = [[JUNK_HEX_PAD, NATIVE_ADDR]]
    signed_call_cf(cf, cf.vault.deployAndFetchBatch, deployFetchParams)

    # Use a non-used salt to get a different address
    depositAddr = getCreate2Addr(
        cf.vault.address,
        cleanHexStrPad(web3.toHex(1)),
        Deposit,
        cleanHexStrPad(NATIVE_ADDR),
    )
    fetchParamsArray = [[depositAddr, NON_ZERO_ADDR]]
    transferParams = [[NATIVE_ADDR, cf.ALICE, TEST_AMNT]]
    args = (fetchParamsArray, transferParams)

    with reverts():
        signed_call_cf(cf, cf.vault.allBatchV2, *args)
