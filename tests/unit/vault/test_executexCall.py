from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy
import random


@given(
    st_srcChain=strategy("uint32"),
    st_srcAddress=strategy("bytes"),
    st_message=strategy("bytes"),
    st_sender=strategy("address"),
)
def test_executexCall(
    cf,
    cfTester,
    st_sender,
    st_srcChain,
    st_srcAddress,
    st_message,
):
    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT)

    startBalVault = cf.vault.balance()
    startBalRecipient = cfTester.balance()

    message = hexStr(st_message)
    args = [
        cfTester.address,
        st_srcChain,
        st_srcAddress,
        message,
    ]
    tx = signed_call_cf(cf, cf.vault.executexCall, *args, sender=st_sender)

    assert cf.vault.balance() == startBalVault
    assert cfTester.balance() == startBalRecipient

    assert tx.events["ReceivedxCall"][0].values() == [
        st_srcChain,
        hexStr(st_srcAddress),
        message,
        0,
    ]


# token contract doesn't have the cfReceivexCall function implemented
def test_executexCall_rev_noCfReceive(cf, token):
    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT)
    randToken = random.choice([NATIVE_ADDR, token])

    args = [
        randToken,
        JUNK_INT,
        JUNK_HEX,
        JUNK_HEX,
    ]
    with reverts():
        signed_call_cf(cf, cf.vault.executexCall, *args)


def test_executexCall_rev_nzAddrs(cf):
    args = [
        ZERO_ADDR,
        JUNK_INT,
        JUNK_HEX,
        JUNK_HEX,
    ]
    with reverts(REV_MSG_NZ_ADDR):
        signed_call_cf(cf, cf.vault.executexCall, *args)


def test_executexCallEth_rev_msgHash(cf):
    args = [
        NON_ZERO_ADDR,
        JUNK_INT,
        JUNK_HEX,
        JUNK_HEX,
    ]

    sigData = AGG_SIGNER_1.getSigDataWithNonces(
        cf.keyManager, cf.vault.executexCall, nonces, *args
    )

    sigData_modif = sigData[:]
    sigData_modif[0] += 1
    with reverts(REV_MSG_SIG):
        cf.vault.executexCall(sigData_modif, *args, {"from": cf.ALICE})

    sigData_modif = sigData[:]
    sigData_modif[1] += 1
    with reverts(REV_MSG_SIG):
        cf.vault.executexCall(sigData_modif, *args, {"from": cf.ALICE})

    sigData_modif = sigData[:]
    sigData_modif[2] = NON_ZERO_ADDR
    with reverts(REV_MSG_SIG):
        cf.vault.executexCall(sigData_modif, *args, {"from": cf.ALICE})


# rev if cfReceiver reverts the call
def test_executexCallEth_rev_CFReceiver(cf, cfReceiverFailMock):
    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT)

    args = [
        cfReceiverFailMock.address,
        JUNK_INT,
        JUNK_HEX,
        JUNK_HEX,
    ]
    with reverts(REV_MSG_CFREC_REVERTED):
        signed_call_cf(cf, cf.vault.executexCall, *args)


# If user contract catches the external reversion, balances are not affected
def test_executexCallEth_tryCatch(cf, cfReceiverTryMock):
    cf.SAFEKEEPER.transfer(cf.vault)

    startBalVault = cf.vault.balance()
    startBalRecipient = cfReceiverTryMock.balance()

    args = [
        cfReceiverTryMock.address,
        JUNK_INT,
        JUNK_HEX,
        JUNK_HEX,
    ]

    tx = signed_call_cf(cf, cf.vault.executexCall, *args)
    assert tx.events["FailedExternalCall"]["revertString"] == REV_MSG_CFREC_REVERTED

    # Check that ETH amount is transferred to the dstAddress
    assert cf.vault.balance() == startBalVault
    assert cfReceiverTryMock.balance() == startBalRecipient
