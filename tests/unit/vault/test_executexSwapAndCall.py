from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy
import random

# NOTE: There is several ways to pass bytes as a message in the arguments:
# 1. JUNKHEX =>  web3.toHex(<int>).
#    paramter value = 0xa455. Returned the same from event => Can be compared
# 2. coming from brownie strategy("bytes")
#    parameter value = b'\x05'. Event returns 0x00 => origi value must be converted
#    to hex via hexString() to be compared.
# 3. hexStr(st_message), when st_message is a strategy("bytes")
#    parameter value = 0x00. Returned the same from event => Can be compared

# NOTE: The signing of the message rev (check msgHash) when the st_srcAddr is an
#       empty string. So min_size is set to 1 to avoid this issue. I expect this to be
#       a brownie/python test issue. In reality we should be able to send xCall with
#       empty message.
# TODO : To be tested when CF validators do the signing.


@given(
    st_srcChain=strategy("uint32"),
    st_srcAddress=strategy("string", min_size=1),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_sender=strategy("address"),
)
def test_executexSwapAndCallEth(
    cf,
    cfReceiverMock,
    st_sender,
    st_srcChain,
    st_srcAddress,
    st_message,
    st_amount,
):
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)

    startBalVault = cf.vault.balance()
    assert startBalVault >= st_amount
    startBalRecipient = cfReceiverMock.balance()

    message = hexStr(st_message)
    args = [
        [ETH_ADDR, cfReceiverMock.address, st_amount],
        st_srcChain,
        st_srcAddress,
        message,
    ]
    tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args, sender=st_sender)

    assert cf.vault.balance() - startBalVault == -st_amount
    assert cfReceiverMock.balance() - startBalRecipient == st_amount

    assert tx.events["ReceivedxSwapAndCall"][0].values() == [
        st_srcChain,
        st_srcAddress,
        message,
        ETH_ADDR,
        st_amount,
        st_amount,
    ]


# token contract doesn't have the cfRecieve function implemented
def test_executexSwapAndCall_rev_noCfReceive(cf, token):
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)
    randToken = random.choice([ETH_ADDR, token])

    startBalVault = cf.vault.balance()
    startBalRecipient = cf.ALICE.balance()

    args = [
        [randToken, token, TEST_AMNT],
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]
    with reverts():
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    assert cf.vault.balance() == startBalVault
    assert cf.ALICE.balance() == startBalRecipient


# rev if token address is not an ERC20
def test_executexSwapAndCall_revToken(cf, cfReceiverMock):
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)

    startBalVault = cf.vault.balance()
    startBalRecipient = cf.ALICE.balance()

    args = [
        [NON_ZERO_ADDR, cfReceiverMock.address, TEST_AMNT],
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]
    with reverts():
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    assert cf.vault.balance() == startBalVault
    assert cf.ALICE.balance() == startBalRecipient


# Trying to send ETH when there's none in the Vault
def test_executexSwapAndCallEth_rev_not_enough_eth(cf, cfReceiverMock):
    args = [
        [ETH_ADDR, cfReceiverMock, TEST_AMNT],
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]
    with reverts():
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)


def test_executexSwapAndCall_rev_nzAddrs(cf, cfReceiverMock, token):
    args = [
        [ZERO_ADDR, cfReceiverMock, TEST_AMNT],
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]
    with reverts(REV_MSG_NZ_ADDR):
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    args = [
        [ETH_ADDR, ZERO_ADDR, TEST_AMNT],
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]
    with reverts(REV_MSG_NZ_ADDR):
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    args = [
        [token, ZERO_ADDR, TEST_AMNT],
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]
    with reverts(REV_MSG_NZ_ADDR):
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)


def test_executexSwapAndCall_rev_nzAmount(cf, cfReceiverMock, token):
    args = [
        [ETH_ADDR, cfReceiverMock, 0],
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]
    with reverts(REV_MSG_NZ_UINT):
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    args = [
        [token, cfReceiverMock, 0],
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]
    with reverts(REV_MSG_NZ_UINT):
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)


def test_executexSwapAndCallEth_rev_msgHash(cf):
    args = [
        [ETH_ADDR, cf.ALICE, TEST_AMNT],
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]
    callDataNoSig = cf.vault.executexSwapAndCall.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[2] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.vault.executexSwapAndCall(sigData, *args)


# rev if cfReceiver reverts the call
def test_executexSwapAndCallEth_rev_CFReceiver(cf, cfReceiverFailMock):
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)

    startBalVault = cf.vault.balance()
    startBalRecipient = cfReceiverFailMock.balance()

    args = [
        [ETH_ADDR, cfReceiverFailMock.address, TEST_AMNT],
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]
    with reverts(REV_MSG_REVERTED):
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    assert cf.vault.balance() == startBalVault
    assert cfReceiverFailMock.balance() == startBalRecipient


# If user contract catches the external reversion, the eth is transferred anyway.
@given(
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
)
def test_executexSwapAndCallEth_tryCatch(cf, cfReceiverTryMock, st_amount):
    cf.DEPLOYER.transfer(cf.vault, st_amount)

    startBalVault = cf.vault.balance()
    startBalRecipient = cfReceiverTryMock.balance()

    args = [
        [ETH_ADDR, cfReceiverTryMock.address, st_amount],
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]

    tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)
    assert tx.events["FailedExternalCall"]["revertString"] == REV_MSG_REVERTED

    # Check that ETH amount is transferred to the dstAddress
    assert cf.vault.balance() - startBalVault == -st_amount
    assert cfReceiverTryMock.balance() - startBalRecipient == st_amount


# If user contract catches the external reversion, the tokens are transferred anyway.
@given(
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
)
def test_executexSwapAndCallToken_tryCatch(cf, cfReceiverTryMock, st_amount, token):
    token.transfer(cf.vault, TEST_AMNT, {"from": cf.DEPLOYER})

    startBalVault = token.balanceOf(cf.vault)
    startBalRecipient = token.balanceOf(cfReceiverTryMock)

    args = [
        [token, cfReceiverTryMock.address, st_amount],
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]

    tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)
    assert tx.events["FailedExternalCall"]["revertString"] == REV_MSG_REVERTED

    # Check that the token amount is transferred to the dstAddress
    assert token.balanceOf(cf.vault) - startBalVault == -st_amount
    assert token.balanceOf(cfReceiverTryMock) - startBalRecipient == st_amount


# Analogous tests for executexSwapAndCall but with tokens instead of ETH


@given(
    st_srcChain=strategy("uint32"),
    st_srcAddress=strategy("string", min_size=1),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_sender=strategy("address"),
)
def test_executexSwapAndCallEth(
    cf,
    cfReceiverMock,
    st_sender,
    st_srcChain,
    st_srcAddress,
    st_message,
    st_amount,
    token,
):
    token.transfer(cf.vault, st_amount, {"from": cf.DEPLOYER})

    startBalVault = token.balanceOf(cf.vault)
    assert startBalVault >= st_amount
    startBalRecipient = token.balanceOf(cfReceiverMock)

    message = hexStr(st_message)
    args = [
        [token, cfReceiverMock.address, st_amount],
        st_srcChain,
        st_srcAddress,
        message,
    ]
    tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args, sender=st_sender)

    # Check that the token amount is transferred to the dstAddress
    assert token.balanceOf(cf.vault) - startBalVault == -st_amount
    assert token.balanceOf(cfReceiverMock) - startBalRecipient == st_amount

    assert tx.events["ReceivedxSwapAndCall"][0].values() == [
        st_srcChain,
        st_srcAddress,
        message,
        token,
        st_amount,
        0,
    ]
