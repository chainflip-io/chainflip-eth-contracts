from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy


# NOTE: There is several ways to pass bytes as a message in the arguments:
# 1. JUNKHEX =>  web3.toHex(<int>).
#    paramter value = 0xa455. Returned the same from event => Can be compared
# 2. coming from brownie strategy("bytes")
#    parameter value = b'\x05'. Event returns 0x00 => origi value must be converted
#    to hex via hexString() to be compared.
# 3. hexStr(st_message), when st_message is a strategy("bytes")
#    parameter value = 0x00. Returned the same from event => Can be compared

# NOTE: The signing of the message fails (check msgHash) when the st_srcAddr is an
#       empty string. So min_size is set to 1 to avoid this issue.
# TODO: I expect this to be a brownie/python test issue. In reality we should be able
#       to send xCall with empty message. To be tested with the real network.


@given(
    st_srcChain=strategy("uint32"),
    st_srcAddress=strategy("string", min_size=1),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_sender=strategy("address"),
)
def test_xSwapETHxCall(
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
def test_xSwapETHxCall_failsEth(cf, token):
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)

    startBalVault = cf.vault.balance()
    startBalRecipient = cf.ALICE.balance()

    args = [
        [ETH_ADDR, token, TEST_AMNT],
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]
    with reverts():
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    assert cf.vault.balance() == startBalVault
    assert cf.ALICE.balance() == startBalRecipient


# fails if token address is not an ERC20
def test_xSwapETHxCall_failsToken(cf, cfReceiverMock):
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
def test_xSwapETHxCall_fails_not_enough_eth(cf, cfReceiverMock):
    args = [
        [ETH_ADDR, cfReceiverMock, TEST_AMNT],
        JUNK_INT,
        JUNK_STR,
        JUNK_HEX,
    ]
    with reverts():
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)


# fails if cfReceiver reverts the call
def test_xSwapETHxCall_fails_CFReceiver(cf, cfReceiverFailMock):
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


# If user contract catches the external reverstion, the eth is transferred anyway.
@given(
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
)
def test_xSwapETHxCall_tryCatchETH(cf, cfReceiverTryMock, st_amount):
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


# TODO: Do all the analogous tests for xSwapTokenxCall


# def test_transfer_token(cf, token):
#     token.transfer(cf.vault, TEST_AMNT, {"from": cf.DEPLOYER})

#     startBalVault = token.balanceOf(cf.vault)
#     startBalRecipient = token.balanceOf(cf.ALICE)

#     args = [[token, cf.ALICE, TEST_AMNT]]
#     signed_call_cf(cf, cf.vault.transfer, *args)

#     assert token.balanceOf(cf.vault) - startBalVault == -TEST_AMNT
#     assert token.balanceOf(cf.ALICE) - startBalRecipient == TEST_AMNT


# def test_transfer_rev_tokenAddr(cf):
#     with reverts(REV_MSG_NZ_ADDR):
#         args = [[ZERO_ADDR, cf.ALICE, TEST_AMNT]]
#         signed_call_cf(cf, cf.vault.transfer, *args)


# def test_transfer_rev_recipient(cf):
#     with reverts(REV_MSG_NZ_ADDR):
#         args = [[ETH_ADDR, ZERO_ADDR, TEST_AMNT]]
#         signed_call_cf(cf, cf.vault.transfer, *args)


# def test_transfer_rev_amount(cf):
#     with reverts(REV_MSG_NZ_UINT):
#         args = [[ETH_ADDR, cf.ALICE, 0]]
#         signed_call_cf(cf, cf.vault.transfer, *args)


# def test_transfer_rev_msgHash(cf):
#     callDataNoSig = cf.vault.transfer.encode_input(
#         agg_null_sig(cf.keyManager.address, chain.id), [ETH_ADDR, cf.ALICE, TEST_AMNT]
#     )
#     sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
#     sigData[2] += 1

#     with reverts(REV_MSG_MSGHASH):
#         cf.vault.transfer(sigData, [ETH_ADDR, cf.ALICE, TEST_AMNT])


# def test_transfer_rev_sig(cf):
#     callDataNoSig = cf.vault.transfer.encode_input(
#         agg_null_sig(cf.keyManager.address, chain.id), [ETH_ADDR, cf.ALICE, TEST_AMNT]
#     )
#     sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
#     sigData[3] += 1

#     with reverts(REV_MSG_SIG):
#         cf.vault.transfer(sigData, [ETH_ADDR, cf.ALICE, TEST_AMNT])
