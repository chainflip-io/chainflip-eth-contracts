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
def test_fetchDepositTokenBatch(
    cf, token, token2, DepositToken, st_amounts, st_swapIDs, st_tokenBools
):
    trimToShortest([st_amounts, st_swapIDs, st_tokenBools])
    tokens = [token if b == True else token2 for b in st_tokenBools]
    tokenATotal = 0
    tokenBTotal = 0

    for am, id, tok in zip(st_amounts, st_swapIDs, tokens):
        # Get the address to deposit to and deposit
        depositAddr = getCreate2Addr(
            cf.vault.address, id.hex(), DepositToken, cleanHexStrPad(tok.address)
        )
        # cf.DEPLOYER.transfer(depositAddr, am)
        tok.transfer(depositAddr, am, {"from": cf.DEPLOYER})
        if tok == token:
            tokenATotal += am
        else:
            tokenBTotal += am

    assert token.balanceOf(cf.vault) == 0
    assert token2.balanceOf(cf.vault) == 0

    # Fetch the deposit
    args = (st_swapIDs, tokens)
    signed_call_cf(cf, cf.vault.fetchDepositTokenBatch, *args)

    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
    assert token.balanceOf(cf.vault) == tokenATotal
    assert token2.balanceOf(cf.vault) == tokenBTotal


def test_fetchDepositTokenBatch_rev_msgHash(cf, token):
    callDataNoSig = cf.vault.fetchDepositTokenBatch.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), [JUNK_HEX_PAD], [token]
    )

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[2] += 1
    # Fetch the deposit
    with reverts(REV_MSG_MSGHASH):
        cf.vault.fetchDepositTokenBatch(sigData, [JUNK_HEX_PAD], [token])


def test_fetchDepositTokenBatch_rev_sig(cf, token):
    callDataNoSig = cf.vault.fetchDepositTokenBatch.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), [JUNK_HEX_PAD], [token]
    )

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[3] += 1
    # Fetch the deposit
    with reverts(REV_MSG_SIG):
        cf.vault.fetchDepositTokenBatch(sigData, [JUNK_HEX_PAD], [token])


def test_fetchDepositTokenBatch_rev_array_length(cf, token):
    with reverts(REV_MSG_V_ARR_LEN):
        args = ([JUNK_HEX_PAD, JUNK_HEX_PAD], [token])
        signed_call_cf(cf, cf.vault.fetchDepositTokenBatch, *args)
