from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy

@given(
    st_dstChain=strategy("uint32"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_sender=strategy("address"),
)
def test_loopback_executexSwapAndCall_native(
    cf, cfDexAggMock, st_sender, st_amount, st_recipient
):


    cf.vault.enableSwaps({"from": cf.gov})


    # Fund Vault
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)


    # Balance => ETH, token1, token2
    balanceVault = web3.eth.get_balance(cf.vault.address)

    # Executing a xSwap
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
