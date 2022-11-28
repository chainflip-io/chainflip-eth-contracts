from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy
import random


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

    (dexMock, dexAggMock) = cfDexAggMock

    # Fund Vault and DexMock
    token.transfer(cf.vault, st_amount * 10, {"from": cf.DEPLOYER})
    token2.transfer(dexMock, st_amount * 10, {"from": cf.DEPLOYER})

    startBalVault = web3.eth.get_balance(cf.vault.address)
    startBalDexAggMockToken = token.balanceOf(dexAggMock)
    startBalDexAggMockToken2 = token2.balanceOf(dexAggMock)
    startBalDexMockToken = token.balanceOf(dexAggMock)
    startBalDexMockToken2 = token2.balanceOf(dexAggMock)

    token.approve(cf.vault, st_amount, {"from": st_sender})

    tx = dexAggMock.xSwapNativeAndCall(
        st_dstChain,
        hexStr(dexAggMock.address),
        token.symbol(),
        st_sender,
        token,
        token2,
        st_recipient,
        {"from": st_sender, "amount": st_amount},
    )

    assert web3.eth.get_balance(cf.vault.address) == startBalVault + st_amount

    # TODO: Continue here

    assert tx.events["SwapNativeAndCall"][0].values() == [
        st_dstChain,
        st_dstAddress,
        st_swapIntent,
        st_amount,
        st_sender,
        hexStr(st_message),
        st_refundAddress,
    ]
