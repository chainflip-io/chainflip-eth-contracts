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


@given(
    st_srcChain=strategy("uint32"),
    st_srcAddress=strategy("bytes"),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_sender=strategy("address"),
)
def test_executexSwapAndCallNative(
    cf,
    cfTester,
    st_sender,
    st_srcChain,
    st_srcAddress,
    st_message,
    st_amount,
):
    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT)

    startBalVault = cf.vault.balance()
    assert startBalVault >= st_amount
    startBalRecipient = cfTester.balance()

    message = hexStr(st_message)
    args = [
        [NATIVE_ADDR, cfTester.address, st_amount],
        st_srcChain,
        st_srcAddress,
        message,
    ]
    tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args, sender=st_sender)

    assert cf.vault.balance() - startBalVault == -st_amount
    assert cfTester.balance() - startBalRecipient == st_amount

    assert tx.events["ReceivedxSwapAndCall"][0].values() == [
        st_srcChain,
        hexStr(st_srcAddress),
        message,
        NATIVE_ADDR,
        st_amount,
        st_amount,
        0,
    ]


# token contract doesn't have the cfReceive function implemented
def test_executexSwapAndCall_rev_noCfReceive(cf, token):
    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT)
    randToken = random.choice([NATIVE_ADDR, token])

    startBalVault = cf.vault.balance()
    startBalRecipient = cf.ALICE.balance()

    args = [
        [randToken, token, TEST_AMNT],
        JUNK_INT,
        JUNK_HEX,
        JUNK_HEX,
    ]
    with reverts():
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    assert cf.vault.balance() == startBalVault
    assert cf.ALICE.balance() == startBalRecipient


# rev if token address is not an ERC20
def test_executexSwapAndCall_revToken(cf, cfTester):
    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT)

    startBalVault = cf.vault.balance()
    startBalRecipient = cf.ALICE.balance()

    args = [
        [NON_ZERO_ADDR, cfTester.address, TEST_AMNT],
        JUNK_INT,
        JUNK_HEX,
        JUNK_HEX,
    ]
    with reverts():
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    assert cf.vault.balance() == startBalVault
    assert cf.ALICE.balance() == startBalRecipient


# Trying to send ETH when there's none in the Vault
def test_executexSwapAndCallNative_rev_not_enough_eth(cf, cfTester):
    args = [
        [NATIVE_ADDR, cfTester, TEST_AMNT],
        JUNK_INT,
        JUNK_HEX,
        JUNK_HEX,
    ]
    with reverts():
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)


def test_executexSwapAndCall_rev_nzAddrs(cf, cfTester, token):
    args = [
        [ZERO_ADDR, cfTester, TEST_AMNT],
        JUNK_INT,
        JUNK_HEX,
        JUNK_HEX,
    ]
    with reverts(REV_MSG_NZ_ADDR):
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    args = [
        [NATIVE_ADDR, ZERO_ADDR, TEST_AMNT],
        JUNK_INT,
        JUNK_HEX,
        JUNK_HEX,
    ]
    with reverts(REV_MSG_NZ_ADDR):
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    args = [
        [token, ZERO_ADDR, TEST_AMNT],
        JUNK_INT,
        JUNK_HEX,
        JUNK_HEX,
    ]
    with reverts(REV_MSG_NZ_ADDR):
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)


def test_executexSwapAndCall_nzAmount(cf, cfTester, token):
    args = [
        [NATIVE_ADDR, cfTester, 0],
        JUNK_INT,
        JUNK_HEX,
        JUNK_HEX,
    ]
    signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)


def test_executexSwapAndCallNative_rev_msgHash(cf):
    args = [
        [NATIVE_ADDR, cf.ALICE, TEST_AMNT],
        JUNK_INT,
        JUNK_HEX,
        JUNK_HEX,
    ]

    sigData = AGG_SIGNER_1.getSigDataWithNonces(
        cf.keyManager, cf.vault.executexSwapAndCall, nonces, *args
    )

    sigData_modif = sigData[:]
    sigData_modif[0] += 1
    with reverts(REV_MSG_SIG):
        cf.vault.executexSwapAndCall(sigData_modif, *args, {"from": cf.ALICE})

    sigData_modif = sigData[:]
    sigData_modif[1] += 1
    with reverts(REV_MSG_SIG):
        cf.vault.executexSwapAndCall(sigData_modif, *args, {"from": cf.ALICE})

    sigData_modif = sigData[:]
    sigData_modif[2] = NON_ZERO_ADDR
    with reverts(REV_MSG_SIG):
        cf.vault.executexSwapAndCall(sigData_modif, *args, {"from": cf.ALICE})


# rev if cfReceiver reverts the call
def test_executexSwapAndCallNative_rev_CFReceiver(cf, cfReceiverFailMock):
    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT)

    startBalVault = cf.vault.balance()
    startBalRecipient = cfReceiverFailMock.balance()

    args = [
        [NATIVE_ADDR, cfReceiverFailMock.address, TEST_AMNT],
        JUNK_INT,
        JUNK_HEX,
        JUNK_HEX,
    ]
    with reverts(REV_MSG_CFREC_REVERTED):
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    assert cf.vault.balance() == startBalVault
    assert cfReceiverFailMock.balance() == startBalRecipient


# If user contract catches the external reversion, the eth is transferred anyway.
@given(
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
)
def test_executexSwapAndCallNative_tryCatch(cf, cfReceiverTryMock, st_amount):
    cf.SAFEKEEPER.transfer(cf.vault, st_amount)

    startBalVault = cf.vault.balance()
    startBalRecipient = cfReceiverTryMock.balance()

    args = [
        [NATIVE_ADDR, cfReceiverTryMock.address, st_amount],
        JUNK_INT,
        JUNK_HEX,
        JUNK_HEX,
    ]

    tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)
    assert tx.events["FailedExternalCall"]["revertString"] == REV_MSG_CFREC_REVERTED

    # Check that ETH amount is transferred to the dstAddress
    assert cf.vault.balance() - startBalVault == -st_amount
    assert cfReceiverTryMock.balance() - startBalRecipient == st_amount


# If user contract catches the external reversion, the tokens are transferred anyway.
@given(
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
)
def test_executexSwapAndCallToken_tryCatch(cf, cfReceiverTryMock, st_amount, token):
    token.transfer(cf.vault, TEST_AMNT, {"from": cf.SAFEKEEPER})

    startBalVault = token.balanceOf(cf.vault)
    startBalRecipient = token.balanceOf(cfReceiverTryMock)

    args = [
        [token, cfReceiverTryMock.address, st_amount],
        JUNK_INT,
        JUNK_HEX,
        JUNK_HEX,
    ]

    tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)
    assert tx.events["FailedExternalCall"]["revertString"] == REV_MSG_CFREC_REVERTED

    # Check that the token amount is transferred to the dstAddress
    assert token.balanceOf(cf.vault) - startBalVault == -st_amount
    assert token.balanceOf(cfReceiverTryMock) - startBalRecipient == st_amount


# Analogous tests for executexSwapAndCall but with tokens instead of ETH


@given(
    st_srcChain=strategy("uint32"),
    st_srcAddress=strategy("bytes"),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_sender=strategy("address"),
)
def test_executexSwapAndCallToken(
    cf,
    cfTester,
    st_sender,
    st_srcChain,
    st_srcAddress,
    st_message,
    st_amount,
    token,
):
    token.transfer(cf.vault, st_amount, {"from": cf.SAFEKEEPER})

    startBalVault = token.balanceOf(cf.vault)
    assert startBalVault >= st_amount
    startBalRecipient = token.balanceOf(cfTester)

    message = hexStr(st_message)
    args = [
        [token, cfTester.address, st_amount],
        st_srcChain,
        st_srcAddress,
        message,
    ]
    tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args, sender=st_sender)

    # Check that the token amount is transferred to the dstAddress
    assert token.balanceOf(cf.vault) - startBalVault == -st_amount
    assert token.balanceOf(cfTester) - startBalRecipient == st_amount

    assert tx.events["ReceivedxSwapAndCall"][0].values() == [
        st_srcChain,
        hexStr(st_srcAddress),
        message,
        token,
        st_amount,
        0,
        0,
    ]


def test_executexSwapAndCallToken_gasTest(
    cf,
    cfTester,
    token,
):
    # Hardcode variables to speed up the test
    srcChain = 1
    amount = TEST_AMNT
    st_srcAddress = bytes.fromhex(cf.ALICE.address[2:])

    token.transfer(cf.vault, amount * 2, {"from": cf.SAFEKEEPER})

    # Currently the gasLimit is hardcoded at 400k in the state chain.
    message = encode_abi(["string", "uint256"], ["GasTest", 210000])
    args = [
        [token, cfTester.address, amount],
        srcChain,
        st_srcAddress,
        message,
    ]
    sigData = AGG_SIGNER_1.getSigDataWithNonces(
        cf.keyManager, cf.vault.executexSwapAndCall, nonces, *args
    )
    cf.vault.executexSwapAndCall(
        sigData,
        *args,
        {"from": cf.ALICE, "gas": 400000},
    )

    message = encode_abi(["string", "uint256"], ["GasTest", 230000])
    args = [
        [token, cfTester.address, amount],
        srcChain,
        st_srcAddress,
        message,
    ]
    sigData = AGG_SIGNER_1.getSigDataWithNonces(
        cf.keyManager, cf.vault.executexSwapAndCall, nonces, *args
    )

    # Reverts - run out of gas
    with reverts(""):
        cf.vault.executexSwapAndCall(
            sigData,
            *args,
            {"from": cf.ALICE, "gas": 400000},
        )
