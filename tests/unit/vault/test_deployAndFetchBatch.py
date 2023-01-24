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
def test_deployAndFetchBatch(cf, token, Deposit, st_amounts, st_swapIDs, st_tokenBools):
    trimToShortest([st_amounts, st_swapIDs, st_tokenBools])
    tokens = [token if b == True else NATIVE_ADDR for b in st_tokenBools]
    tokenTotal = 0
    nativeTotal = 0

    for am, id, tok in zip(st_amounts, st_swapIDs, tokens):
        # Get the address to deposit to and deposit
        if tok == token:
            depositAddr = getCreate2Addr(
                cf.vault.address, id.hex(), Deposit, cleanHexStrPad(tok.address)
            )
            tok.transfer(depositAddr, am, {"from": cf.DEPLOYER})
            tokenTotal += am
        else:
            depositAddr = getCreate2Addr(
                cf.vault.address, id.hex(), Deposit, cleanHexStrPad(tok)
            )
            cf.DEPLOYER.transfer(depositAddr, am)
            nativeTotal += am

    assert token.balanceOf(cf.vault) == 0
    assert web3.eth.get_balance(cf.vault.address) == 0

    # Fetch the deposit
    deployFetchParams = [craftDeployFetchParamsArray(st_swapIDs, tokens)]

    signed_call_cf(cf, cf.vault.deployAndFetchBatch, *deployFetchParams)

    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
    assert token.balanceOf(cf.vault.address) == tokenTotal
    assert web3.eth.get_balance(cf.vault.address) == nativeTotal


def test_deployAndFetchBatch_token_rev_msgHash(cf, token):
    for tok in [token, NATIVE_ADDR]:
        callDataNoSig = cf.vault.deployAndFetchBatch.encode_input(
            agg_null_sig(cf.keyManager.address, chain.id), [[JUNK_HEX_PAD, tok]]
        )

        sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
        sigData[2] += 1
        # Fetch the deposit
        with reverts(REV_MSG_MSGHASH):
            cf.vault.deployAndFetchBatch(sigData, [[JUNK_HEX_PAD, tok]])


def test_deployAndFetchBatch_rev_sig(cf, token):
    for tok in [token, NATIVE_ADDR]:
        callDataNoSig = cf.vault.deployAndFetchBatch.encode_input(
            agg_null_sig(cf.keyManager.address, chain.id), [[JUNK_HEX_PAD, tok]]
        )

        sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
        sigData[3] += 1
        # Fetch the deposit
        with reverts(REV_MSG_SIG):
            cf.vault.deployAndFetchBatch(sigData, [[JUNK_HEX_PAD, tok]])


# Deploying a Deposit on an address that already contains a Deposit should revert.
def test_deployAndFetchBatch_rev_deployed(cf, token):
    for tok in [token, NATIVE_ADDR]:
        signed_call_cf(cf, cf.vault.deployAndFetchBatch, [[JUNK_HEX_PAD, tok]])
        with reverts():
            signed_call_cf(cf, cf.vault.deployAndFetchBatch, [[JUNK_HEX_PAD, tok]])
