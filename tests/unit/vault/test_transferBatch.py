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
    tokens = choices([NATIVE_ADDR, token, token2], k=minLen)

    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT * minLen)
    token.transfer(cf.vault, TEST_AMNT * minLen, {"from": cf.SAFEKEEPER})
    token2.transfer(cf.vault, TEST_AMNT * minLen, {"from": cf.SAFEKEEPER})

    nativeBals = [recip.balance() for recip in st_recipients]
    tokenBals = [token.balanceOf(recip) for recip in st_recipients]
    token2Bals = [token2.balanceOf(recip) for recip in st_recipients]

    transferParamsArray = [craftTransferParamsArray(tokens, st_recipients, st_amounts)]

    signed_call_cf(cf, cf.vault.transferBatch, *transferParamsArray, sender=st_sender)

    for i in range(len(st_recipients)):
        if tokens[i] == NATIVE_ADDR:
            assert st_recipients[i].balance() == nativeBals[i] + st_amounts[i]
        elif tokens[i] == token:
            assert token.balanceOf(st_recipients[i]) == tokenBals[i] + st_amounts[i]
        elif tokens[i] == token2:
            assert token2.balanceOf(st_recipients[i]) == token2Bals[i] + st_amounts[i]
        else:
            assert False, "Panic"


def test_transferBatch_rev_sig(cf):
    args = [[NATIVE_ADDR, cf.ALICE, TEST_AMNT]]
    sigData = AGG_SIGNER_1.getSigDataWithNonces(
        cf.keyManager, cf.vault.transferBatch, nonces, args
    )

    sigData_modif = sigData[:]
    sigData_modif[0] += 1
    with reverts(REV_MSG_SIG):
        cf.vault.transferBatch(sigData_modif, args, {"from": cf.ALICE})

    sigData_modif = sigData[:]
    sigData_modif[1] += 1
    with reverts(REV_MSG_SIG):
        cf.vault.transferBatch(sigData_modif, args, {"from": cf.ALICE})

    sigData_modif = sigData[:]
    sigData_modif[2] = NON_ZERO_ADDR
    with reverts(REV_MSG_SIG):
        cf.vault.transferBatch(sigData_modif, args, {"from": cf.ALICE})
