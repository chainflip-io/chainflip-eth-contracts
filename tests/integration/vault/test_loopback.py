from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy


@given(
    st_srcChain=strategy("uint32"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_sender=strategy("address"),
    st_srcAddress=strategy("string", min_size=1),
    st_message=strategy("bytes"),
)
def test_loopback_executexSwapAndCall_native(
    cf, cfLoopbackMock, st_sender, st_amount, st_message, st_srcChain, st_srcAddress
):

    cf.vault.enablexCalls({"from": cf.gov})

    # Fund Vault
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)

    # Native Balance
    balanceVault = web3.eth.get_balance(cf.vault.address)
    balanceLoopback = web3.eth.get_balance(cfLoopbackMock.address)

    # Executing a xSwap
    args = [
        [NATIVE_ADDR, cfLoopbackMock, st_amount],
        st_srcChain,
        st_srcAddress,
        st_message,
    ]

    # Ensuring the st_sender is sending the transaction so it doesn't interfere with the receipient's eth balance
    tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args, sender=st_sender)

    # Check that the Vault receives the callback
    assert tx.events["XCallNative"]["dstChain"] == st_srcChain
    assert tx.events["XCallNative"]["dstAddress"] == st_srcAddress
    assert tx.events["XCallNative"]["swapIntent"] == "USDC"
    assert tx.events["XCallNative"]["amount"] == st_amount
    assert tx.events["XCallNative"]["sender"] == cfLoopbackMock.address
    assert tx.events["XCallNative"]["refundAddress"] == cfLoopbackMock.address

    assert balanceVault == web3.eth.get_balance(cf.vault.address)

    assert balanceLoopback == web3.eth.get_balance(cfLoopbackMock.address)


@given(
    st_srcChain=strategy("uint32"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_sender=strategy("address"),
    st_srcAddress=strategy("string", min_size=1),
    st_message=strategy("bytes"),
)
def test_loopback_executexSwapAndCall_token(
    cf,
    cfLoopbackMock,
    st_sender,
    st_amount,
    st_message,
    st_srcChain,
    st_srcAddress,
    token,
):

    cf.vault.enablexCalls({"from": cf.gov})

    # Fund Vault
    token.transfer(cf.vault, st_amount, {"from": cf.DEPLOYER})

    # token Balance
    balanceVault = token.balanceOf(cf.vault.address)
    balanceLoopback = token.balanceOf(cfLoopbackMock.address)

    # Executing a xSwap
    args = [
        [token, cfLoopbackMock, st_amount],
        st_srcChain,
        st_srcAddress,
        st_message,
    ]

    # Ensuring the st_sender is sending the transaction so it doesn't interfere with the receipient's eth balance
    tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args, sender=st_sender)

    # Check that the Vault receives the callback
    assert tx.events["XCallToken"]["dstChain"] == st_srcChain
    assert tx.events["XCallToken"]["dstAddress"] == st_srcAddress
    assert tx.events["XCallToken"]["swapIntent"] == "USDC"
    assert tx.events["XCallToken"]["srcToken"] == token.address
    assert tx.events["XCallToken"]["amount"] == st_amount
    assert tx.events["XCallToken"]["sender"] == cfLoopbackMock.address
    assert tx.events["XCallToken"]["refundAddress"] == cfLoopbackMock.address

    assert balanceVault == token.balanceOf(cf.vault.address)
    assert balanceLoopback == token.balanceOf(cfLoopbackMock.address)


@given(
    st_srcChain=strategy("uint32"),
    st_sender=strategy("address"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_srcAddress=strategy("string", min_size=1),
    st_message=strategy("bytes"),
)
def test_loopback_executexCall_native(
    cf, cfLoopbackMock, st_sender, st_amount, st_message, st_srcChain, st_srcAddress
):

    cf.vault.enablexCalls({"from": cf.gov})

    # Fund Loopback
    cf.DEPLOYER.transfer(cfLoopbackMock, st_amount)

    # Native Balance
    balanceVault = web3.eth.get_balance(cf.vault.address)
    assert web3.eth.get_balance(cfLoopbackMock.address) == st_amount

    # Executing a xCall
    args = [
        cfLoopbackMock,
        st_srcChain,
        st_srcAddress,
        st_message,
    ]

    # Ensuring the st_sender is sending the transaction so it doesn't interfere with the receipient's eth balance
    tx = signed_call_cf(cf, cf.vault.executexCall, *args, sender=st_sender)

    # Check that the Vault receives the callback
    assert tx.events["XCallNative"]["dstChain"] == st_srcChain
    assert tx.events["XCallNative"]["dstAddress"] == st_srcAddress
    assert tx.events["XCallNative"]["swapIntent"] == ""
    assert tx.events["XCallNative"]["amount"] == st_amount
    assert tx.events["XCallNative"]["sender"] == cfLoopbackMock.address
    assert tx.events["XCallNative"]["refundAddress"] == cfLoopbackMock.address

    assert balanceVault == web3.eth.get_balance(cf.vault.address) - st_amount
    assert web3.eth.get_balance(cfLoopbackMock.address) == 0
