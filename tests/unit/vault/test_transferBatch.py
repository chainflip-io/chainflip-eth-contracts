from consts import *
from brownie import reverts
from brownie.test import given, strategy
from random import choices


@given(
    recipients=strategy('address[]', unique=True),
    amounts=strategy('uint[]', max_value=TEST_AMNT),
    sender=strategy('address')
)
def test_transferBatch(cf, token, token2, recipients, amounts, sender):
    recipients = [recip for recip in recipients if recip != cf.vault.address and recip != sender]
    # Make sure that they're all the same length
    minLen = trimToShortest([recipients, amounts])
    tokens = choices([ETH_ADDR, token, token2], k=minLen)

    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT * minLen)
    token.transfer(cf.vault, TEST_AMNT * minLen, {'from': cf.DEPLOYER})
    token2.transfer(cf.vault, TEST_AMNT * minLen, {'from': cf.DEPLOYER})

    ethBals = [recip.balance() for recip in recipients]
    tokenBals = [token.balanceOf(recip) for recip in recipients]
    token2Bals = [token2.balanceOf(recip) for recip in recipients]

    callDataNoSig = cf.vault.transferBatch.encode_input(agg_null_sig(cf.keyManager.address, chain.id), tokens, recipients, amounts)
    balanceBefore = sender.balance()
    tx = cf.vault.transferBatch(AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), tokens, recipients, amounts, {'from': sender})
    balanceAfter = sender.balance()
    txRefundTest(balanceBefore, balanceAfter, tx)

    for i in range(len(recipients)):
        if tokens[i] == ETH_ADDR:
            assert recipients[i].balance() == ethBals[i] + amounts[i]
        elif tokens[i] == token:
            assert token.balanceOf(recipients[i]) == tokenBals[i] + amounts[i]
        elif tokens[i] == token2:
            assert token2.balanceOf(recipients[i]) == token2Bals[i] + amounts[i]
        else:
            assert False, "Panic"


@given(
    recipients=strategy('address[]', unique=True),
    amounts=strategy('uint[]', max_value=TEST_AMNT),
    sender=strategy('address'),
    randK=strategy('uint', min_value=1, max_value=100)
)
def test_transferBatch_rev_array_length(cf, token, token2, recipients, amounts, sender, randK):
    # Make sure the lengths are always different somewhere
    k = len(amounts) if len(recipients) != len(amounts) else len(amounts) + randK
    tokens = choices([ETH_ADDR, token, token2], k=k)
    callDataNoSig = cf.vault.transferBatch.encode_input(agg_null_sig(cf.keyManager.address, chain.id), tokens, recipients, amounts)

    with reverts(REV_MSG_V_ARR_LEN):
        cf.vault.transferBatch(AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), tokens, recipients, amounts)


def test_transferBatch_rev_msgHash(cf):
    callDataNoSig = cf.vault.transferBatch.encode_input(agg_null_sig(cf.keyManager.address, chain.id), [ETH_ADDR], [cf.ALICE], [TEST_AMNT])
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[0] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.vault.transferBatch(sigData, [ETH_ADDR], [cf.ALICE], [TEST_AMNT])


def test_transferBatch_rev_sig(cf):
    callDataNoSig = cf.vault.transferBatch.encode_input(agg_null_sig(cf.keyManager.address, chain.id), [ETH_ADDR], [cf.ALICE], [TEST_AMNT])
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[1] += 1

    with reverts(REV_MSG_SIG):
        cf.vault.transferBatch(sigData, [ETH_ADDR], [cf.ALICE], [TEST_AMNT])