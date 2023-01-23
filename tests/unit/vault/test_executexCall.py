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


# token contract doesn't have the cfReceivexCall function implemented
def test_executexCall_rev_noCfReceive(cf, token):
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)
    randToken = random.choice([NATIVE_ADDR, token])

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


# If user contract catches the external reversion, balances are not affected
def test_executexCallEth_tryCatch(cf, cfReceiverTryMock):
    cf.DEPLOYER.transfer(cf.vault)

    startBalVault = cf.vault.balance()
    startBalRecipient = cfReceiverTryMock.balance()

    args = [
        cfReceiverTryMock.address,
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]

    tx = signed_call_cf(cf, cf.vault.executexCall, *args)
    assert tx.events["FailedExternalCall"]["revertString"] == REV_MSG_CFREC_REVERTED

    # Check that ETH amount is transferred to the dstAddress
    assert cf.vault.balance() == startBalVault
    assert cfReceiverTryMock.balance() == startBalRecipient
