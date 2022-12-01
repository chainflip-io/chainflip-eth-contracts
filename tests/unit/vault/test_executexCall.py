from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy
import random


@given(
    st_srcChain=strategy("uint32"),
    st_srcAddress=strategy("string", min_size=1),
    st_message=strategy("bytes"),
    st_sender=strategy("address"),
)
def test_executexCall(
    cf,
    cfReceiverMock,
    st_sender,
    st_srcChain,
    st_srcAddress,
    st_message,
):
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)

    startBalVault = cf.vault.balance()
    startBalRecipient = cfReceiverMock.balance()

    message = hexStr(st_message)
    args = [
        cfReceiverMock.address,
        st_srcChain,
        st_srcAddress,
        message,
    ]
    tx = signed_call_cf(cf, cf.vault.executexCall, *args, sender=st_sender)

    assert cf.vault.balance() == startBalVault
    assert cfReceiverMock.balance() == startBalRecipient

    assert tx.events["ReceivedxCall"][0].values() == [
        st_srcChain,
        st_srcAddress,
        message,
    ]


# token contract doesn't have the cfRecievexCall function implemented
def test_executexCall_rev_noCfReceive(cf, token):
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)
    randToken = random.choice([ETH_ADDR, token])

    args = [
        randToken,
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]
    with reverts():
        signed_call_cf(cf, cf.vault.executexCall, *args)


def test_executexCall_rev_nzAddrs(cf, token):
    args = [
        ZERO_ADDR,
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]
    with reverts(REV_MSG_NZ_ADDR):
        signed_call_cf(cf, cf.vault.executexCall, *args)


def test_executexCallEth_rev_msgHash(cf):
    args = [
        NON_ZERO_ADDR,
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]
    callDataNoSig = cf.vault.executexCall.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[2] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.vault.executexCall(sigData, *args)


# rev if cfReceiver reverts the call
def test_executexCallEth_rev_CFReceiver(cf, cfReceiverFailMock):
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)

    args = [
        cfReceiverFailMock.address,
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]
    with reverts(REV_MSG_CFREC_REVERTED):
        signed_call_cf(cf, cf.vault.executexCall, *args)


# # If user contract catches the external reversion, the eth is transferred anyway.
# @given(
#     st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
# )
# def test_executexCallEth_tryCatch(cf, cfReceiverTryMock, st_amount):
#     cf.DEPLOYER.transfer(cf.vault, st_amount)

#     startBalVault = cf.vault.balance()
#     startBalRecipient = cfReceiverTryMock.balance()

#     args = [
#         [ETH_ADDR, cfReceiverTryMock.address, st_amount],
#         JUNK_INT,
#         JUNK_STR,
#         JUNK_HEX,
#     ]

#     tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)
#     assert tx.events["FailedExternalCall"]["revertString"] == REV_MSG_CFREC_REVERTED

#     # Check that ETH amount is transferred to the dstAddress
#     assert cf.vault.balance() - startBalVault == -st_amount
#     assert cfReceiverTryMock.balance() - startBalRecipient == st_amount


# # If user contract catches the external reversion, the tokens are transferred anyway.
# @given(
#     st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
# )
# def test_executexCallToken_tryCatch(cf, cfReceiverTryMock, st_amount, token):
#     token.transfer(cf.vault, TEST_AMNT, {"from": cf.DEPLOYER})

#     startBalVault = token.balanceOf(cf.vault)
#     startBalRecipient = token.balanceOf(cfReceiverTryMock)

#     args = [
#         [token, cfReceiverTryMock.address, st_amount],
#         JUNK_INT,
#         JUNK_STR,
#         JUNK_HEX,
#     ]

#     tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)
#     assert tx.events["FailedExternalCall"]["revertString"] == REV_MSG_CFREC_REVERTED

#     # Check that the token amount is transferred to the dstAddress
#     assert token.balanceOf(cf.vault) - startBalVault == -st_amount
#     assert token.balanceOf(cfReceiverTryMock) - startBalRecipient == st_amount


# # Analogous tests for executexSwapAndCall but with tokens instead of ETH


# @given(
#     st_srcChain=strategy("uint32"),
#     st_srcAddress=strategy("string", min_size=1),
#     st_message=strategy("bytes"),
#     st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
#     st_sender=strategy("address"),
# )
# def test_executexCallEth(
#     cf,
#     cfReceiverMock,
#     st_sender,
#     st_srcChain,
#     st_srcAddress,
#     st_message,
#     st_amount,
#     token,
# ):
#     token.transfer(cf.vault, st_amount, {"from": cf.DEPLOYER})

#     startBalVault = token.balanceOf(cf.vault)
#     assert startBalVault >= st_amount
#     startBalRecipient = token.balanceOf(cfReceiverMock)

#     message = hexStr(st_message)
#     args = [
#         [token, cfReceiverMock.address, st_amount],
#         st_srcChain,
#         st_srcAddress,
#         message,
#     ]
#     tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args, sender=st_sender)

#     # Check that the token amount is transferred to the dstAddress
#     assert token.balanceOf(cf.vault) - startBalVault == -st_amount
#     assert token.balanceOf(cfReceiverMock) - startBalRecipient == st_amount

#     assert tx.events["ReceivedxSwapAndCall"][0].values() == [
#         st_srcChain,
#         st_srcAddress,
#         message,
#         token,
#         st_amount,
#         0,
#     ]
