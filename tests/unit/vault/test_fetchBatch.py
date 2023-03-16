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
    signed_call_cf(cf, cf.vault.deployAndFetchBatch, *deployFetchParams)

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
    signed_call_cf(cf, cf.vault.fetchBatch, *fetchBatchParamsArray)

    assert token.balanceOf(cf.vault.address) == tokenTotal
    assert web3.eth.get_balance(cf.vault.address) == nativeTotal

    for addr in depositAddrs:
        assert web3.eth.get_balance(web3.toChecksumAddress(addr)) == 0
        ## Check that there are contracts in the deposit Addresses
        assert web3.eth.get_code(web3.toChecksumAddress(addr)).hex() != "0x"


def test_fetchBatch_token_rev_msgHash(cf, token):
    for tok in [token, NATIVE_ADDR]:
        callDataNoSig = cf.vault.fetchBatch.encode_input(
            agg_null_sig(cf.keyManager.address, chain.id), [[NON_ZERO_ADDR, tok]]
        )

        sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
        sigData[2] += 1
        # Fetch the deposit
        with reverts(REV_MSG_MSGHASH):
            cf.vault.fetchBatch(sigData, [[NON_ZERO_ADDR, tok]], {"from": cf.ALICE})


def test_fetchBatch_rev_sig(cf, token):
    for tok in [token, NATIVE_ADDR]:
        callDataNoSig = cf.vault.fetchBatch.encode_input(
            agg_null_sig(cf.keyManager.address, chain.id), [[NON_ZERO_ADDR, tok]]
        )

        sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
        sigData[3] += 1
        # Fetch the deposit
        with reverts(REV_MSG_SIG):
            cf.vault.fetchBatch(sigData, [[NON_ZERO_ADDR, tok]], {"from": cf.ALICE})


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
def test_fetchBatch_rev_noFunction(cf, token):
    # Using the keyManager as a proxy for a deployed contract without a fetch function
    for tok in [token, NATIVE_ADDR]:

        if tok == token:
            tok.transfer(cf.keyManager.address, TEST_AMNT, {"from": cf.SAFEKEEPER})
        else:
            cf.SAFEKEEPER.transfer(cf.keyManager.address, TEST_AMNT)

        with reverts():
            signed_call_cf(cf, cf.vault.fetchBatch, [[cf.keyManager.address, tok]])

        if tok == token:
            assert tok.balanceOf(cf.keyManager.address) == TEST_AMNT
        else:
            assert web3.eth.get_balance(cf.keyManager.address) == TEST_AMNT
