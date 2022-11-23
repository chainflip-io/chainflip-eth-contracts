from brownie import reverts, web3
from brownie.test import given, strategy
from consts import *
from shared_tests import *


# Tests enable and disable swaps


@given(
    st_sender=strategy("address"),
)
def test_enableSwaps_rev_gov(cf, st_sender):
    assert cf.vault.getSwapsEnabled() == False
    if st_sender == cf.gov:
        cf.vault.enableSwaps({"from": st_sender})
        assert cf.vault.getSwapsEnabled() == True
    else:
        with reverts(REV_MSG_GOV_GOVERNOR):
            cf.vault.enableSwaps({"from": st_sender})
            assert cf.vault.getSwapsEnabled() == False


def test_enableSwaps_rev_enabled(cf):
    cf.vault.enableSwaps({"from": cf.gov})

    with reverts(REV_MSG_VAULT_SWAPS_EN):
        cf.vault.enableSwaps({"from": cf.gov})


@given(
    st_sender=strategy("address"),
)
def test_disableSwaps_rev_gov(cf, st_sender):
    assert cf.vault.getSwapsEnabled() == False
    cf.vault.enableSwaps({"from": cf.gov})
    assert cf.vault.getSwapsEnabled() == True
    if st_sender == cf.gov:
        cf.vault.disableSwaps({"from": st_sender})
        assert cf.vault.getSwapsEnabled() == False
    else:
        with reverts(REV_MSG_GOV_GOVERNOR):
            cf.vault.disableSwaps({"from": st_sender})
            assert cf.vault.getSwapsEnabled() == True


def test_enableSwaps_rev_disabled(cf):
    with reverts(REV_MSG_VAULT_SWAPS_DIS):
        cf.vault.disableSwaps({"from": cf.gov})


# xSwapTokenAndCall


@given(
    st_dstChain=strategy("uint32"),
    st_dstAddress=strategy("string"),
    st_swapIntent=strategy("string"),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", max_value=TEST_AMNT),
    st_refundAddress=strategy("address"),
    st_sender=strategy("address"),
)
def test_swapTokenAndCall(
    cf,
    st_dstChain,
    st_dstAddress,
    st_swapIntent,
    st_message,
    token,
    st_amount,
    st_refundAddress,
    st_sender,
):
    cf.vault.enableSwaps({"from": cf.gov})

    if st_amount == 0:
        with reverts(REV_MSG_NZ_UINT):
            cf.vault.xSwapTokenAndCall(
                st_dstChain,
                st_dstAddress,
                st_swapIntent,
                st_message,
                token,
                st_amount,
                st_refundAddress,
                {"from": st_sender},
            )
    else:
        # Fund st_sender account
        token.transfer(st_sender, st_amount)

        iniBalance = token.balanceOf(st_sender)

        token.approve(cf.vault, st_amount, {"from": st_sender})
        tx = cf.vault.xSwapTokenAndCall(
            st_dstChain,
            st_dstAddress,
            st_swapIntent,
            st_message,
            token,
            st_amount,
            st_refundAddress,
            {"from": st_sender},
        )
        assert token.balanceOf(st_sender) == iniBalance - st_amount
        assert tx.events["SwapTokenAndCall"][0].values() == [
            st_dstChain,
            st_dstAddress,
            st_swapIntent,
            token,
            st_amount,
            st_sender,
            hexStr(st_message),
            st_refundAddress,
        ]


@given(
    st_dstChain=strategy("uint32"),
    st_dstAddress=strategy("string"),
    st_swapIntent=strategy("string"),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_refundAddress=strategy("address"),
    st_sender=strategy("address"),
)
def test_swapTokenAndCall_rev_bal(
    cf,
    st_dstChain,
    st_dstAddress,
    st_swapIntent,
    st_message,
    token,
    st_amount,
    st_refundAddress,
    st_sender,
):
    cf.vault.enableSwaps({"from": cf.gov})
    if st_sender != cf.DEPLOYER:
        with reverts(REV_MSG_ERC20_EXCEED_BAL):
            cf.vault.xSwapTokenAndCall(
                st_dstChain,
                st_dstAddress,
                st_swapIntent,
                st_message,
                token,
                st_amount,
                st_refundAddress,
                {"from": st_sender},
            )


@given(
    st_dstChain=strategy("uint32"),
    st_dstAddress=strategy("string"),
    st_swapIntent=strategy("string"),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_refundAddress=strategy("address"),
    st_sender=strategy("address"),
)
def test_swapTokenAndCall_rev_suspended(
    cf,
    st_dstChain,
    st_dstAddress,
    st_swapIntent,
    st_message,
    token,
    st_amount,
    st_refundAddress,
    st_sender,
):
    cf.vault.suspend({"from": cf.gov})
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.xSwapTokenAndCall(
            st_dstChain,
            st_dstAddress,
            st_swapIntent,
            st_message,
            token,
            st_amount,
            st_refundAddress,
            {"from": st_sender},
        )


@given(
    st_dstChain=strategy("uint32"),
    st_dstAddress=strategy("string"),
    st_swapIntent=strategy("string"),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_refundAddress=strategy("address"),
    st_sender=strategy("address"),
)
def test_swapTokenAndCall_rev_disabled(
    cf,
    st_dstChain,
    st_dstAddress,
    st_swapIntent,
    st_message,
    token,
    st_amount,
    st_refundAddress,
    st_sender,
):
    with reverts(REV_MSG_VAULT_SWAPS_DIS):
        cf.vault.xSwapTokenAndCall(
            st_dstChain,
            st_dstAddress,
            st_swapIntent,
            st_message,
            token,
            st_amount,
            st_refundAddress,
            {"from": st_sender},
        )


# xSwapNativeAndCall


@given(
    st_dstChain=strategy("uint32"),
    st_dstAddress=strategy("string"),
    st_swapIntent=strategy("string"),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", max_value=TEST_AMNT),
    st_refundAddress=strategy("address"),
    st_sender=strategy("address"),
)
def test_swapETHAndCall(
    cf,
    st_sender,
    st_dstChain,
    st_dstAddress,
    st_swapIntent,
    st_message,
    st_amount,
    st_refundAddress,
):
    cf.vault.enableSwaps({"from": cf.gov})
    if st_amount == 0:
        with reverts(REV_MSG_NZ_UINT):
            cf.vault.xSwapNativeAndCall(
                st_dstChain,
                st_dstAddress,
                st_swapIntent,
                st_message,
                st_refundAddress,
                {"from": st_sender, "amount": st_amount},
            )
    else:
        iniBal = web3.eth.get_balance(cf.vault.address)
        tx = cf.vault.xSwapNativeAndCall(
            st_dstChain,
            st_dstAddress,
            st_swapIntent,
            st_message,
            st_refundAddress,
            {"from": st_sender, "amount": st_amount},
        )
        assert web3.eth.get_balance(cf.vault.address) == iniBal + st_amount
        assert tx.events["SwapNativeAndCall"][0].values() == [
            st_dstChain,
            st_dstAddress,
            st_swapIntent,
            st_amount,
            st_sender,
            hexStr(st_message),
            st_refundAddress,
        ]


@given(
    st_dstChain=strategy("uint32"),
    st_dstAddress=strategy("string"),
    st_swapIntent=strategy("string"),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_refundAddress=strategy("address"),
    st_sender=strategy("address"),
)
def test_swapETHAndCall_rev_suspended(
    cf,
    st_sender,
    st_dstChain,
    st_dstAddress,
    st_swapIntent,
    st_message,
    st_amount,
    st_refundAddress,
):
    cf.vault.suspend({"from": cf.gov})
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.xSwapNativeAndCall(
            st_dstChain,
            st_dstAddress,
            st_swapIntent,
            st_message,
            st_refundAddress,
            {"from": st_sender, "amount": st_amount},
        )


@given(
    st_dstChain=strategy("uint32"),
    st_dstAddress=strategy("string"),
    st_swapIntent=strategy("string"),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_refundAddress=strategy("address"),
    st_sender=strategy("address"),
)
def test_swapETHAndCall_rev_disabled(
    cf,
    st_sender,
    st_dstChain,
    st_dstAddress,
    st_swapIntent,
    st_message,
    st_amount,
    st_refundAddress,
):
    with reverts(REV_MSG_VAULT_SWAPS_DIS):
        cf.vault.xSwapNativeAndCall(
            st_dstChain,
            st_dstAddress,
            st_swapIntent,
            st_message,
            st_refundAddress,
            {"from": st_sender, "amount": st_amount},
        )
