from brownie import reverts, web3
from brownie.test import given, strategy
from consts import *
from shared_tests import *


@given(
    st_amounts=strategy(
        "uint[]", max_value=TEST_AMNT, max_length=int(INIT_TOKEN_SUPPLY / TEST_AMNT)
    ),
    st_swapIDs=strategy("bytes32[]", unique=True),
    st_tokenBools=strategy("bool[]"),
)
def test_fetchBatch(cf, token, Deposit, st_amounts, st_swapIDs, st_tokenBools):
    trimToShortest([st_amounts, st_swapIDs, st_tokenBools])
    tokens = [token if b == True else NATIVE_ADDR for b in st_tokenBools]
    tokenTotal = 0
    nativeTotal = 0
    depositAddrs = []

    # Deploy initial Deposit contracts
    deployFetchParams = [craftDeployFetchParamsArray(st_swapIDs, tokens)]
    tx = signed_call_cf(cf, cf.vault.deployAndFetchBatch, *deployFetchParams)

    if tokens.count(NATIVE_ADDR) > 0:
        assert len(tx.events["FetchedNative"]) == tokens.count(NATIVE_ADDR)

    for am, id, tok in zip(st_amounts, st_swapIDs, tokens):
        # Deploy a deposit contract, get the address to deposit to and deposit
        if tok == token:
            depositAddr = getCreate2Addr(
                cf.vault.address, id.hex(), Deposit, cleanHexStrPad(tok.address)
            )
            tok.transfer(depositAddr, am, {"from": cf.SAFEKEEPER})
            tokenTotal += am
        else:
            depositAddr = getCreate2Addr(
                cf.vault.address, id.hex(), Deposit, cleanHexStrPad(tok)
            )
            cf.SAFEKEEPER.transfer(depositAddr, am)
            nativeTotal += am
        depositAddrs.append(depositAddr)

    assert token.balanceOf(cf.vault) == 0
    assert web3.eth.get_balance(cf.vault.address) == 0

    # Fetch the deposit
    fetchBatchParamsArray = [craftFetchParamsArray(depositAddrs, tokens)]
    tx = signed_call_cf(cf, cf.vault.fetchBatch, *fetchBatchParamsArray)

    if tokens.count(NATIVE_ADDR) > 0:
        assert len(tx.events["FetchedNative"]) == tokens.count(NATIVE_ADDR)

    assert token.balanceOf(cf.vault.address) == tokenTotal
    assert web3.eth.get_balance(cf.vault.address) == nativeTotal

    for addr in depositAddrs:
        assert web3.eth.get_balance(web3.toChecksumAddress(addr)) == 0
        ## Check that there are contracts in the deposit Addresses
        assert web3.eth.get_code(web3.toChecksumAddress(addr)).hex() != "0x"


def test_fetchBatch_rev_sig(cf, token):
    for tok in [token, NATIVE_ADDR]:
        args = [[NON_ZERO_ADDR, tok]]

        sigData = AGG_SIGNER_1.getSigDataWithNonces(
            cf.keyManager, cf.vault.fetchBatch, nonces, args
        )

        sigData_modif = sigData[:]
        sigData_modif[0] += 1
        with reverts(REV_MSG_SIG):
            cf.vault.fetchBatch(sigData_modif, args, {"from": cf.ALICE})

        sigData_modif = sigData[:]
        sigData_modif[1] += 1
        with reverts(REV_MSG_SIG):
            cf.vault.fetchBatch(sigData_modif, args, {"from": cf.ALICE})

        sigData_modif = sigData[:]
        sigData_modif[2] = NON_ZERO_ADDR
        with reverts(REV_MSG_SIG):
            cf.vault.fetchBatch(sigData_modif, args, {"from": cf.ALICE})


# Calling the fetch function on a non-deployed contract (empty address) will revert
def test_fetchBatch_rev_notdeployed(cf, token):
    for tok in [token, NATIVE_ADDR]:

        if tok == token:
            tok.transfer(NON_ZERO_ADDR, TEST_AMNT, {"from": cf.SAFEKEEPER})
        else:
            cf.SAFEKEEPER.transfer(NON_ZERO_ADDR, TEST_AMNT)

        with reverts():
            signed_call_cf(cf, cf.vault.fetchBatch, [[NON_ZERO_ADDR, tok]])

        if tok == token:
            assert tok.balanceOf(NON_ZERO_ADDR) == TEST_AMNT
        else:
            assert web3.eth.get_balance(NON_ZERO_ADDR) == TEST_AMNT


# Calling the fetch function on a contract without the fetch function will revert
def test_fetchBatch_rev_noFunction(cf, token, cfLoopbackMock):
    # Using the Loopbback mock as a proxy for a deployed contract without a fetch function
    # that can receive tokens
    for tok in [token, NATIVE_ADDR]:

        if tok == token:
            tok.transfer(cfLoopbackMock.address, TEST_AMNT, {"from": cf.SAFEKEEPER})
        else:
            cf.SAFEKEEPER.transfer(cfLoopbackMock.address, TEST_AMNT)

        with reverts():
            signed_call_cf(cf, cf.vault.fetchBatch, [[cfLoopbackMock.address, tok]])

        if tok == token:
            assert tok.balanceOf(cfLoopbackMock.address) == TEST_AMNT
        else:
            assert web3.eth.get_balance(cfLoopbackMock.address) == TEST_AMNT
