from brownie import reverts, web3
from brownie.test import given, strategy
from consts import *


@given(
    amounts=strategy('uint[]', max_value=TEST_AMNT, max_length=int(INIT_TOKEN_SUPPLY / TEST_AMNT)),
    swapIDs=strategy('bytes32[]', unique=True),
    tokenBools=strategy('bool[]')
)
def test_fetchDepositTokenBatch(cf, token, token2, DepositToken, amounts, swapIDs, tokenBools):
    trimToShortest([amounts, swapIDs, tokenBools])
    tokens = [token if b == True else token2 for b in tokenBools]
    tokenATotal = 0
    tokenBTotal = 0

    for am, id, tok in zip(amounts, swapIDs, tokens):
        # Get the address to deposit to and deposit
        depositAddr = getCreate2Addr(cf.vault.address, id.hex(), DepositToken, cleanHexStrPad(tok.address))
        # cf.DEPLOYER.transfer(depositAddr, am)
        tok.transfer(depositAddr, am, {'from': cf.DEPLOYER})
        if tok == token:
            tokenATotal += am
        else:
            tokenBTotal += am

    assert token.balanceOf(cf.vault) == 0
    assert token2.balanceOf(cf.vault) == 0

    # Sign the tx without a msgHash or sig
    callDataNoSig = cf.vault.fetchDepositTokenBatch.encode_input(agg_null_sig(), swapIDs, tokens)

    # Fetch the deposit
    cf.vault.fetchDepositTokenBatch(AGG_SIGNER_1.getSigData(callDataNoSig), swapIDs, tokens)

    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
    assert token.balanceOf(cf.vault) == tokenATotal
    assert token2.balanceOf(cf.vault) == tokenBTotal


def test_fetchDepositTokenBatch_rev_msgHash(cf, token):
    callDataNoSig = cf.vault.fetchDepositTokenBatch.encode_input(agg_null_sig(), [JUNK_HEX], [token])

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[0] += 1
    # Fetch the deposit
    with reverts(REV_MSG_MSGHASH):
        cf.vault.fetchDepositTokenBatch(sigData, [JUNK_HEX], [token])


def test_fetchDepositTokenBatch_rev_sig(cf, token):
    callDataNoSig = cf.vault.fetchDepositTokenBatch.encode_input(agg_null_sig(), [JUNK_HEX], [token])

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[1] += 1
    # Fetch the deposit
    with reverts(REV_MSG_SIG):
        cf.vault.fetchDepositTokenBatch(sigData, [JUNK_HEX], [token])


def test_fetchDepositTokenBatch_rev_array_length(cf, token):
    callDataNoSig = cf.vault.fetchDepositTokenBatch.encode_input(agg_null_sig(), [JUNK_HEX, JUNK_HEX], [token])
    with reverts(REV_MSG_V_ARR_LEN):
        cf.vault.fetchDepositTokenBatch(AGG_SIGNER_1.getSigData(callDataNoSig), [JUNK_HEX, JUNK_HEX], [token])