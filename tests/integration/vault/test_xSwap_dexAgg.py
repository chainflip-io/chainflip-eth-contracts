from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy
import random

# Swap ETH:Chain1 -> Token:Chain2 -> Token2:Chain2
@given(
    st_dstChain=strategy("uint32"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_sender=strategy("address"),
    st_recipient=strategy("address"),
)
def test_executexSwapNativeAndCall(
    cf, cfDexAggMock, token, token2, st_sender, st_dstChain, st_amount, st_recipient
):
    cf.vault.enableSwaps({"from": cf.gov})

    # Avoid having to calculate the cases in where recipient==sender.
    if st_sender == st_recipient:
        return

    (dexMock, dexAggMock) = cfDexAggMock

    # Fund Vault and DexMock
    token.transfer(cf.vault, st_amount * 10, {"from": cf.DEPLOYER})
    token2.transfer(dexMock, st_amount * 10, {"from": cf.DEPLOYER})

    startBalVault = web3.eth.get_balance(cf.vault.address)
    startBalDexAggMockToken = token.balanceOf(dexAggMock)
    startBalDexAggMockToken2 = token2.balanceOf(dexAggMock)
    startBalDexMockToken = token.balanceOf(dexMock)
    startBalDexMockToken2 = token2.balanceOf(dexMock)
    startBalrecipientToken = token.balanceOf(st_recipient)
    startBalrecipientToken2 = token2.balanceOf(st_recipient)

    token.approve(cf.vault, st_amount, {"from": st_sender})

    tx = dexAggMock.xSwapNativeAndCall(
        st_dstChain,
        hexStr(dexAggMock.address),
        token.symbol(),
        st_sender,
        dexMock,
        token,
        token2,
        st_recipient,
        {"from": st_sender, "amount": st_amount},
    )

    assert web3.eth.get_balance(cf.vault.address) == startBalVault + st_amount
    startBalVault += st_amount

    # Check that the event with the expected values was emitted

    assert tx.events["SwapNativeAndCall"]["dstChain"] == st_dstChain
    assert tx.events["SwapNativeAndCall"]["dstAddress"] == hexStr(dexAggMock.address)
    assert tx.events["SwapNativeAndCall"]["swapIntent"] == token.symbol()
    assert tx.events["SwapNativeAndCall"]["amount"] == st_amount
    assert tx.events["SwapNativeAndCall"]["sender"] == dexAggMock.address
    ##assert tx.events["SwapNativeAndCall"]["message"] == message
    assert tx.events["SwapNativeAndCall"]["refundAddress"] == st_sender

    # Mimick witnessing and executing the xSwap
    # TODO: Make a function that takes as input an event and makes a function call to
    # the vault as the egress swaps. It should probably take a tx, check which of the
    # four events is it (SwapNativeAndCall, SwapNative, SwapTokenAndCall, SwapToken)
    # and do the appropriate egress function call to the vault.

    # We just do a 1:2 ratio CF swap
    egressAmount = st_amount * 2
    message = tx.events["SwapNativeAndCall"]["message"]

    args = [
        [token, dexAggMock, egressAmount],
        1,  # eth source chain == 1
        JUNK_STR,  # sourceAddress to string
        message,
    ]

    signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    assert startBalDexAggMockToken == token.balanceOf(dexAggMock)
    assert startBalDexAggMockToken2 == token2.balanceOf(dexAggMock)
    assert token.balanceOf(dexMock) - startBalDexMockToken == egressAmount
    assert startBalDexMockToken2 - token2.balanceOf(dexMock) == egressAmount * 2
    assert token.balanceOf(st_recipient) == startBalrecipientToken
    assert token2.balanceOf(st_recipient) == startBalrecipientToken2 + egressAmount * 2
