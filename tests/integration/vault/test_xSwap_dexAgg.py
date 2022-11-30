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
def test_executexSwapNativeAndCall(
    cf, cfDexAggMock, token, token2, st_sender, st_dstChain, st_amount, st_recipient
):
    cf.vault.enableSwaps({"from": cf.gov})

    # Avoid having to calculate the cases in where recipient==sender. This test is mimicking
    # cross-chain swaps so the recipient being the same as the sender is impossible.
    if st_sender == st_recipient:
        return

    (dexMock, dexAggSrcMock, dexAggDstMock, srcChain) = cfDexAggMock

    # Fund Vault and DexMock
    token.transfer(cf.vault, st_amount * 10, {"from": cf.DEPLOYER})
    token2.transfer(dexMock, st_amount * 10, {"from": cf.DEPLOYER})

    # Balance => ETH, token1, token2
    # bals = {}
    # for address in [cf.vault, dexMock, dexAggSrcMock, dexAggDstMock]:
    #     bals[address] = []
    #     bals[address].append(web3.eth.get_balance(address.address))
    #     bals[address].append(token.balanceOf(address))
    #     bals[address].append(token2.balanceOf(address))

    balanceVault = [
        web3.eth.get_balance(cf.vault.address),
        token.balanceOf(cf.vault.address),
        token2.balanceOf(cf.vault.address),
    ]
    balanceDexAggSrc = [
        web3.eth.get_balance(dexAggSrcMock.address),
        token.balanceOf(dexAggSrcMock),
        token2.balanceOf(dexAggSrcMock),
    ]
    balanceDexAggDst = [
        web3.eth.get_balance(dexAggDstMock.address),
        token.balanceOf(dexAggDstMock),
        token2.balanceOf(dexAggDstMock),
    ]
    balanceDex = [
        web3.eth.get_balance(dexMock.address),
        token.balanceOf(dexMock),
        token2.balanceOf(dexMock),
    ]
    balanceRecipient = [
        web3.eth.get_balance(st_recipient.address),
        token.balanceOf(st_recipient),
        token2.balanceOf(st_recipient),
    ]

    # Converting dexAggMock.address into a string via hex(...) confuses brownie. It interprets
    # it as an address, which then cases a failure on the function call since it expects a
    # string. To bypass that, the 0x part is removed from the string.

    tx = dexAggSrcMock.swapNativeAndCallViaChainflip(
        st_dstChain,
        hex(dexAggDstMock.address)[2:],
        token.symbol(),
        dexMock,
        token,
        token2,
        st_recipient,
        {"from": st_sender, "amount": st_amount},
    )

    assert balanceVault == [
        web3.eth.get_balance(cf.vault.address) - st_amount,
        token.balanceOf(cf.vault.address),
        token2.balanceOf(cf.vault.address),
    ]
    balanceVault[0] += st_amount
    assert balanceDexAggSrc == [
        web3.eth.get_balance(dexAggSrcMock.address),
        token.balanceOf(dexAggSrcMock),
        token2.balanceOf(dexAggSrcMock),
    ]

    # Check that the event with the expected values was emitted. The message is verified by decoding it on the egress side.
    assert tx.events["SwapNativeAndCall"]["dstChain"] == st_dstChain
    assert (
        tx.events["SwapNativeAndCall"]["dstAddress"] == hex(dexAggDstMock.address)[2:]
    )
    assert tx.events["SwapNativeAndCall"]["swapIntent"] == token.symbol()
    assert tx.events["SwapNativeAndCall"]["amount"] == st_amount
    assert tx.events["SwapNativeAndCall"]["sender"] == dexAggSrcMock.address
    assert tx.events["SwapNativeAndCall"]["refundAddress"] == st_sender

    # Mimick witnessing and executing the xSwap

    # We just do a 1:2 ratio CF swap
    egressAmount = st_amount * 2
    message = tx.events["SwapNativeAndCall"]["message"]

    args = [
        [token, dexAggDstMock, egressAmount],
        srcChain,  # arbitrary source chain
        hex(dexAggSrcMock.address)[2:],  # sourceAddress to string
        message,
    ]

    # Ensuring the st_sender is sending the transaction so it doesn't interfere with the receipient's eth balance
    signed_call_cf(cf, cf.vault.executexSwapAndCall, *args, sender=st_sender)

    assert balanceVault == [
        web3.eth.get_balance(cf.vault.address),
        token.balanceOf(cf.vault.address) + egressAmount,
        token2.balanceOf(cf.vault.address),
    ]
    assert balanceDexAggSrc == [
        web3.eth.get_balance(dexAggSrcMock.address),
        token.balanceOf(dexAggSrcMock),
        token2.balanceOf(dexAggSrcMock),
    ]
    assert balanceDexAggDst == [
        web3.eth.get_balance(dexAggDstMock.address),
        token.balanceOf(dexAggDstMock),
        token2.balanceOf(dexAggDstMock),
    ]
    assert balanceDex == [
        web3.eth.get_balance(dexMock.address),
        token.balanceOf(dexMock) - egressAmount,
        token2.balanceOf(dexMock) + egressAmount * 2,
    ]
    assert balanceRecipient == [
        web3.eth.get_balance(st_recipient.address),
        token.balanceOf(st_recipient),
        token2.balanceOf(st_recipient) - egressAmount * 2,
    ]


from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy

# Swap Token:Chain1 -> Native:Chain2 -> Token2:Chain2
@given(
    st_dstChain=strategy("uint32"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_sender=strategy("address"),
    st_recipient=strategy("address"),
)
def test_executexSwapTokenAndCall(
    cf, cfDexAggMock, token, token2, st_sender, st_dstChain, st_amount, st_recipient
):
    cf.vault.enableSwaps({"from": cf.gov})

    # Avoid having to calculate the cases in where recipient==sender. This test is mimicking
    # cross-chain swaps so the recipient being the same as the sender is impossible.
    if st_sender == st_recipient:
        return

    (dexMock, dexAggSrcMock, dexAggDstMock, srcChain) = cfDexAggMock

    # Fund Vault and DexMock
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)
    token.transfer(st_sender, st_amount * 10, {"from": cf.DEPLOYER})
    token2.transfer(dexMock, st_amount * 10, {"from": cf.DEPLOYER})

    # Balance => ETH, token1, token2
    balanceVault = [
        web3.eth.get_balance(cf.vault.address),
        token.balanceOf(cf.vault.address),
        token2.balanceOf(cf.vault.address),
    ]
    balanceDexAggSrc = [
        web3.eth.get_balance(dexAggSrcMock.address),
        token.balanceOf(dexAggSrcMock),
        token2.balanceOf(dexAggSrcMock),
    ]
    balanceDexAggDst = [
        web3.eth.get_balance(dexAggDstMock.address),
        token.balanceOf(dexAggDstMock),
        token2.balanceOf(dexAggDstMock),
    ]
    balanceDex = [
        web3.eth.get_balance(dexMock.address),
        token.balanceOf(dexMock),
        token2.balanceOf(dexMock),
    ]
    balanceRecipient = [
        web3.eth.get_balance(st_recipient.address),
        token.balanceOf(st_recipient),
        token2.balanceOf(st_recipient),
    ]

    token.approve(cf.vault, st_amount, {"from": st_sender})

    # Converting dexAggMock.address into a string via hex(...) confuses brownie. It interprets
    # it as an address, which then cases a failure on the function call since it expects a
    # string. To bypass that, the 0x part is removed from the string.
    ethSymbol = "ETH"
    tx = dexAggSrcMock.swapTokenAndCallViaChainflip(
        st_dstChain,
        hex(dexAggDstMock.address)[2:],
        ethSymbol,
        dexMock,
        token2,
        st_recipient,
        token,
        st_amount,
        {"from": st_sender},
    )

    assert balanceVault == [
        web3.eth.get_balance(cf.vault.address),
        token.balanceOf(cf.vault.address) - st_amount,
        token2.balanceOf(cf.vault.address),
    ]
    balanceVault[1] += st_amount
    assert balanceDexAggSrc == [
        web3.eth.get_balance(dexAggSrcMock.address),
        token.balanceOf(dexAggSrcMock),
        token2.balanceOf(dexAggSrcMock),
    ]

    # Check that the event with the expected values was emitted. The message is verified by decoding it on the egress side.
    assert tx.events["SwapNativeAndCall"]["dstChain"] == st_dstChain
    assert (
        tx.events["SwapNativeAndCall"]["dstAddress"] == hex(dexAggDstMock.address)[2:]
    )
    assert tx.events["SwapNativeAndCall"]["swapIntent"] == ethSymbol
    assert tx.events["SwapNativeAndCall"]["amount"] == st_amount
    assert tx.events["SwapNativeAndCall"]["sender"] == dexAggSrcMock.address
    assert tx.events["SwapNativeAndCall"]["refundAddress"] == st_sender

    # Mimick witnessing and executing the xSwap

    # We just do a 1:2 ratio CF swap
    egressAmount = st_amount * 2
    message = tx.events["SwapNativeAndCall"]["message"]

    args = [
        [token, dexAggDstMock, egressAmount],
        srcChain,  # arbitrary source chain
        hex(dexAggSrcMock.address)[2:],  # sourceAddress to string
        message,
    ]

    # Ensuring the st_sender is sending the transaction so it doesn't interfere with the receipient's eth balance
    signed_call_cf(cf, cf.vault.executexSwapAndCall, *args, sender=st_sender)

    assert balanceVault == [
        web3.eth.get_balance(cf.vault.address),
        token.balanceOf(cf.vault.address) + egressAmount,
        token2.balanceOf(cf.vault.address),
    ]
    assert balanceDexAggSrc == [
        web3.eth.get_balance(dexAggSrcMock.address),
        token.balanceOf(dexAggSrcMock),
        token2.balanceOf(dexAggSrcMock),
    ]
    assert balanceDexAggDst == [
        web3.eth.get_balance(dexAggDstMock.address),
        token.balanceOf(dexAggDstMock),
        token2.balanceOf(dexAggDstMock),
    ]
    assert balanceDex == [
        web3.eth.get_balance(dexMock.address),
        token.balanceOf(dexMock) - egressAmount,
        token2.balanceOf(dexMock) + egressAmount * 2,
    ]
    assert balanceRecipient == [
        web3.eth.get_balance(st_recipient.address),
        token.balanceOf(st_recipient),
        token2.balanceOf(st_recipient) - egressAmount * 2,
    ]
