from consts import *
from brownie import reverts
from brownie.test import given, strategy
from random import choices
from shared_tests import *


@given(
    st_recipients=strategy("address[]", unique=True),
    st_amounts=strategy("uint[]", max_value=TEST_AMNT),
    st_sender=strategy("address"),
)
def test_transferBatch(cf, token, token2, st_recipients, st_amounts, st_sender):
    st_recipients = [
        recip
        for recip in st_recipients
        if recip != cf.vault.address and recip != st_sender
    ]
    # Make sure that they're all the same length
    minLen = trimToShortest([st_recipients, st_amounts])
    tokens = choices([ETH_ADDR, token, token2], k=minLen)

    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT * minLen)
    token.transfer(cf.vault, TEST_AMNT * minLen, {"from": cf.DEPLOYER})
    token2.transfer(cf.vault, TEST_AMNT * minLen, {"from": cf.DEPLOYER})

    ethBals = [recip.balance() for recip in st_recipients]
    tokenBals = [token.balanceOf(recip) for recip in st_recipients]
    token2Bals = [token2.balanceOf(recip) for recip in st_recipients]

    args = (tokens, st_recipients, st_amounts)
    signed_call_aggSigner(cf, cf.vault.transferBatch, *args, sender=st_sender)

    for i in range(len(st_recipients)):
        if tokens[i] == ETH_ADDR:
            assert st_recipients[i].balance() == ethBals[i] + st_amounts[i]
        elif tokens[i] == token:
            assert token.balanceOf(st_recipients[i]) == tokenBals[i] + st_amounts[i]
        elif tokens[i] == token2:
            assert token2.balanceOf(st_recipients[i]) == token2Bals[i] + st_amounts[i]
        else:
            assert False, "Panic"


@given(
    st_recipients=strategy("address[]", unique=True),
    st_amounts=strategy("uint[]", max_value=TEST_AMNT),
    st_sender=strategy("address"),
    randK=strategy("uint", min_value=1, max_value=100),
)
def test_transferBatch_rev_tokensArray_length(
    cf, token, token2, st_recipients, st_amounts, st_sender, randK
):
    # Make sure the lengths are always different somewhere
    k = (
        len(st_amounts)
        if len(st_recipients) != len(st_amounts)
        else len(st_amounts) + randK
    )
    tokens = choices([ETH_ADDR, token, token2], k=k)

    with reverts(REV_MSG_V_ARR_LEN):
        args = (tokens, st_recipients, st_amounts)
        signed_call_aggSigner(cf, cf.vault.transferBatch, *args, sender=st_sender)


@given(
    st_recipients=strategy("address[]", unique=True),
    st_amounts=strategy("uint[]", max_value=TEST_AMNT),
    st_sender=strategy("address"),
    randK=strategy("uint", min_value=1, max_value=100),
)
def test_transferBatch_rev_st_amountsArray_length(
    cf, token, token2, st_recipients, st_amounts, st_sender, randK
):
    # Make sure the lengths are always different somewhere
    k = len(st_recipients)
    tokens = choices([ETH_ADDR, token, token2], k=k)
    st_amountsModif = choices(st_amounts, k=k + randK)

    with reverts(REV_MSG_V_ARR_LEN):
        args = (tokens, st_recipients, st_amountsModif)
        signed_call_aggSigner(cf, cf.vault.transferBatch, *args)


def test_transferBatch_rev_msgHash(cf):
    callDataNoSig = cf.vault.transferBatch.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        [ETH_ADDR],
        [cf.ALICE],
        [TEST_AMNT],
    )
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[2] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.vault.transferBatch(sigData, [ETH_ADDR], [cf.ALICE], [TEST_AMNT])


def test_transferBatch_rev_sig(cf):
    callDataNoSig = cf.vault.transferBatch.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        [ETH_ADDR],
        [cf.ALICE],
        [TEST_AMNT],
    )
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[3] += 1

    with reverts(REV_MSG_SIG):
        cf.vault.transferBatch(sigData, [ETH_ADDR], [cf.ALICE], [TEST_AMNT])
