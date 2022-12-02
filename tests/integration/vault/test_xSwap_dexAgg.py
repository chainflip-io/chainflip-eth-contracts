from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy

# Swap ETH:Chain1 -> Token:Chain2 -> Token2:Chain2
@given(
    st_dstChain=strategy("uint32"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_sender=strategy("address"),
    st_recipient=strategy("address"),
)
def test_dex_executexCallNative(
    cf, cfDexAggMock, token, token2, st_sender, st_dstChain, st_amount, st_recipient
):
    cf.vault.enablexCalls({"from": cf.gov})

    # Avoid having to calculate the cases in where recipient==sender. This test is mimicking
    # cross-chain swaps so the recipient being the same as the sender is impossible.
    if st_sender == st_recipient:
        return

    (dexMock, dexAggSrcMock, dexAggDstMock, srcChain) = cfDexAggMock

    # Fund Vault and DexMock
    token.transfer(cf.vault, st_amount * 10, {"from": cf.DEPLOYER})
    token2.transfer(dexMock, st_amount * 10, {"from": cf.DEPLOYER})

    # Balance => ETH, token1, token2
    bals = {}
    for address in [cf.vault, dexMock, dexAggSrcMock, dexAggDstMock, st_recipient]:
        bals[address] = []
        bals[address].append(web3.eth.get_balance(address.address))
        bals[address].append(token.balanceOf(address))
        bals[address].append(token2.balanceOf(address))

    # Converting dexAggMock.address into a string via toHex(...) confuses brownie. It interprets
    # it as an address, which then cases a failure on the function call since it expects a
    # string. To bypass that, the 0x part is removed from the string.

    tx = dexAggSrcMock.swapNativeAndCallViaChainflip(
        st_dstChain,
        toHex(dexAggDstMock.address)[2:],
        token.symbol(),
        dexMock,
        token,
        token2,
        st_recipient,
        {"from": st_sender, "amount": st_amount},
    )

    assert bals[cf.vault] == [
        web3.eth.get_balance(cf.vault.address) - st_amount,
        token.balanceOf(cf.vault.address),
        token2.balanceOf(cf.vault.address),
    ]
    bals[cf.vault][0] += st_amount
    assert bals[dexAggSrcMock] == [
        web3.eth.get_balance(dexAggSrcMock.address),
        token.balanceOf(dexAggSrcMock),
        token2.balanceOf(dexAggSrcMock),
    ]

    # Check that the event with the expected values was emitted. The message is verified by decoding it on the egress side.
    assert tx.events["XCallNative"]["dstChain"] == st_dstChain
    assert tx.events["XCallNative"]["dstAddress"] == toHex(dexAggDstMock.address)[2:]
    assert tx.events["XCallNative"]["swapIntent"] == token.symbol()
    assert tx.events["XCallNative"]["amount"] == st_amount
    assert tx.events["XCallNative"]["sender"] == dexAggSrcMock.address
    assert tx.events["XCallNative"]["refundAddress"] == st_sender

    # Mimick witnessing and executing the xSwap

    # We just do a 1:2 ratio CF swap
    egressAmount = st_amount * 2
    message = tx.events["XCallNative"]["message"]

    args = [
        [token, dexAggDstMock, egressAmount],
        srcChain,  # arbitrary source chain
        toHex(dexAggSrcMock.address)[2:],  # sourceAddress to string
        message,
    ]

    # Ensuring the st_sender is sending the transaction so it doesn't interfere with the receipient's eth balance
    signed_call_cf(cf, cf.vault.executexSwapAndCall, *args, sender=st_sender)

    assert bals[cf.vault] == [
        web3.eth.get_balance(cf.vault.address),
        token.balanceOf(cf.vault.address) + egressAmount,
        token2.balanceOf(cf.vault.address),
    ]
    assert bals[dexAggSrcMock] == [
        web3.eth.get_balance(dexAggSrcMock.address),
        token.balanceOf(dexAggSrcMock),
        token2.balanceOf(dexAggSrcMock),
    ]
    assert bals[dexAggDstMock] == [
        web3.eth.get_balance(dexAggDstMock.address),
        token.balanceOf(dexAggDstMock),
        token2.balanceOf(dexAggDstMock),
    ]
    assert bals[dexMock] == [
        web3.eth.get_balance(dexMock.address),
        token.balanceOf(dexMock) - egressAmount,
        token2.balanceOf(dexMock) + egressAmount * 2,
    ]
    assert bals[st_recipient] == [
        web3.eth.get_balance(st_recipient.address),
        token.balanceOf(st_recipient),
        token2.balanceOf(st_recipient) - egressAmount * 2,
    ]


# Swap Token:Chain1 -> Native:Chain2 -> Token2:Chain2
@given(
    st_dstChain=strategy("uint32"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_sender=strategy("address"),
    st_recipient=strategy("address"),
)
def test_dex_executexCallToken(
    cf, cfDexAggMock, token, token2, st_sender, st_dstChain, st_amount, st_recipient
):
    cf.vault.enablexCalls({"from": cf.gov})

    # Avoid having to calculate the cases in where recipient==sender. This test is mimicking
    # cross-chain swaps so the recipient being the same as the sender is impossible.
    if st_sender == st_recipient:
        return

    (dexMock, dexAggSrcMock, dexAggDstMock, srcChain) = cfDexAggMock

    # Fund Vault, DexMock
    cf.DEPLOYER.transfer(cf.vault, st_amount * 10)
    token.transfer(st_sender, st_amount * 10, {"from": cf.DEPLOYER})
    token2.transfer(dexMock, st_amount * 10, {"from": cf.DEPLOYER})

    # Balance => ETH, token1, token2
    bals = {}
    for address in [cf.vault, dexMock, dexAggSrcMock, dexAggDstMock, st_recipient]:
        bals[address] = []
        bals[address].append(web3.eth.get_balance(address.address))
        bals[address].append(token.balanceOf(address))
        bals[address].append(token2.balanceOf(address))

    token.approve(dexAggSrcMock, st_amount, {"from": st_sender})

    # Converting dexAggMock.address into a string via toHex(...) confuses brownie. It interprets
    # it as an address, which then cases a failure on the function call since it expects a
    # string. To bypass that, the 0x part is removed from the string.
    ethSymbol = "ETH"
    tx = dexAggSrcMock.swapTokenAndCallViaChainflip(
        st_dstChain,
        toHex(dexAggDstMock.address)[2:],
        ethSymbol,
        dexMock,
        ETH_ADDR,
        token2,
        st_recipient,
        token,
        st_amount,
        {"from": st_sender},
    )

    assert bals[cf.vault] == [
        web3.eth.get_balance(cf.vault.address),
        token.balanceOf(cf.vault.address) - st_amount,
        token2.balanceOf(cf.vault.address),
    ]
    bals[cf.vault][1] += st_amount
    assert bals[dexAggSrcMock] == [
        web3.eth.get_balance(dexAggSrcMock.address),
        token.balanceOf(dexAggSrcMock),
        token2.balanceOf(dexAggSrcMock),
    ]

    # Check that the event with the expected values was emitted. The message is verified by decoding it on the egress side.
    assert tx.events["XCallToken"]["dstChain"] == st_dstChain
    assert tx.events["XCallToken"]["dstAddress"] == toHex(dexAggDstMock.address)[2:]
    assert tx.events["XCallToken"]["swapIntent"] == ethSymbol
    assert tx.events["XCallToken"]["srcToken"] == token.address
    assert tx.events["XCallToken"]["amount"] == st_amount
    assert tx.events["XCallToken"]["sender"] == dexAggSrcMock.address
    assert tx.events["XCallToken"]["refundAddress"] == st_sender

    # Mimick witnessing and executing the xSwap

    # We just do a 1:2 ratio CF swap
    egressAmount = st_amount * 2
    message = tx.events["XCallToken"]["message"]

    args = [
        [ETH_ADDR, dexAggDstMock, egressAmount],
        srcChain,  # arbitrary source chain
        toHex(dexAggSrcMock.address)[2:],  # sourceAddress to string
        message,
    ]

    # Ensuring the st_sender is sending the transaction so it doesn't interfere with the receipient's eth balance
    signed_call_cf(cf, cf.vault.executexSwapAndCall, *args, sender=st_sender)

    assert bals[cf.vault] == [
        web3.eth.get_balance(cf.vault.address) + egressAmount,
        token.balanceOf(cf.vault.address),
        token2.balanceOf(cf.vault.address),
    ]
    assert bals[dexAggSrcMock] == [
        web3.eth.get_balance(dexAggSrcMock.address),
        token.balanceOf(dexAggSrcMock),
        token2.balanceOf(dexAggSrcMock),
    ]
    assert bals[dexAggDstMock] == [
        web3.eth.get_balance(dexAggDstMock.address),
        token.balanceOf(dexAggDstMock),
        token2.balanceOf(dexAggDstMock),
    ]
    assert bals[dexMock] == [
        web3.eth.get_balance(dexMock.address) - egressAmount,
        token.balanceOf(dexMock),
        token2.balanceOf(dexMock) + egressAmount * 2,
    ]
    assert bals[st_recipient] == [
        web3.eth.get_balance(st_recipient.address),
        token.balanceOf(st_recipient),
        token2.balanceOf(st_recipient) - egressAmount * 2,
    ]
