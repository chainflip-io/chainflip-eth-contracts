from brownie import reverts, web3
from brownie.test import given, strategy
from consts import *
from shared_tests import *


# xCallToken and xSwapToken


@given(
    st_dstChain=strategy("uint32"),
    st_dstAddress=strategy("bytes"),
    st_dstToken=strategy("uint16"),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", max_value=TEST_AMNT),
    st_refundAddress=strategy("bytes"),
    st_dstNativeBudget=strategy("uint"),
    st_sender=strategy("address"),
)
def test_swapToken(
    cf,
    st_dstChain,
    st_dstAddress,
    st_dstToken,
    st_message,
    token,
    st_amount,
    st_refundAddress,
    st_dstNativeBudget,
    st_sender,
):

    if st_amount == 0:
        with reverts(REV_MSG_NZ_UINT):
            cf.vault.xSwapToken(
                st_dstChain,
                st_dstAddress,
                st_dstToken,
                token,
                st_amount,
                {"from": st_sender},
            )

        with reverts(REV_MSG_NZ_UINT):
            cf.vault.xCallToken(
                st_dstChain,
                st_dstAddress,
                st_dstToken,
                st_message,
                st_dstNativeBudget,
                token,
                st_amount,
                st_refundAddress,
                {"from": st_sender},
            )

    else:
        # Fund st_sender account
        token.transfer(st_sender, st_amount * 2)

        # xSwapToken
        iniBalance = token.balanceOf(st_sender)

        token.approve(cf.vault, st_amount, {"from": st_sender})
        tx = cf.vault.xSwapToken(
            st_dstChain,
            st_dstAddress,
            st_dstToken,
            token,
            st_amount,
            {"from": st_sender},
        )
        assert token.balanceOf(st_sender) == iniBalance - st_amount
        assert tx.events["SwapToken"][0].values() == [
            st_dstChain,
            hexStr(st_dstAddress),
            st_dstToken,
            token,
            st_amount,
            st_sender,
        ]

        # xCallToken
        iniBalance = token.balanceOf(st_sender)

        token.approve(cf.vault, st_amount, {"from": st_sender})
        tx = cf.vault.xCallToken(
            st_dstChain,
            st_dstAddress,
            st_dstToken,
            st_message,
            st_dstNativeBudget,
            token,
            st_amount,
            st_refundAddress,
            {"from": st_sender},
        )
        assert token.balanceOf(st_sender) == iniBalance - st_amount
        assert tx.events["XCallToken"][0].values() == [
            st_dstChain,
            hexStr(st_dstAddress),
            st_dstToken,
            token,
            st_amount,
            st_sender,
            hexStr(st_message),
            st_dstNativeBudget,
            hexStr(st_refundAddress),
        ]


@given(
    st_dstChain=strategy("uint32"),
    st_dstAddress=strategy("bytes"),
    st_dstToken=strategy("uint16"),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_dstNativeBudget=strategy("uint"),
    st_refundAddress=strategy("bytes"),
    st_sender=strategy("address"),
)
def test_swapToken_rev_bal(
    cf,
    st_dstChain,
    st_dstAddress,
    st_dstToken,
    st_message,
    token,
    st_amount,
    st_dstNativeBudget,
    st_refundAddress,
    st_sender,
):

    if st_sender != cf.DEPLOYER:
        # xSwapToken
        with reverts(REV_MSG_ERC20_EXCEED_BAL):
            cf.vault.xSwapToken(
                st_dstChain,
                st_dstAddress,
                st_dstToken,
                token,
                st_amount,
                {"from": st_sender},
            )

        # xCallToken
        with reverts(REV_MSG_ERC20_EXCEED_BAL):
            cf.vault.xCallToken(
                st_dstChain,
                st_dstAddress,
                st_dstToken,
                st_message,
                st_dstNativeBudget,
                token,
                st_amount,
                st_refundAddress,
                {"from": st_sender},
            )


@given(
    st_dstChain=strategy("uint32"),
    st_dstAddress=strategy("bytes"),
    st_dstToken=strategy("uint16"),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_dstNativeBudget=strategy("uint"),
    st_refundAddress=strategy("bytes"),
    st_sender=strategy("address"),
)
def test_swapToken_rev_suspended(
    cf,
    st_dstChain,
    st_dstAddress,
    st_dstToken,
    st_message,
    token,
    st_amount,
    st_dstNativeBudget,
    st_refundAddress,
    st_sender,
):
    cf.vault.suspend({"from": cf.gov})

    # xCallToken
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.xCallToken(
            st_dstChain,
            st_dstAddress,
            st_dstToken,
            st_message,
            st_dstNativeBudget,
            token,
            st_amount,
            st_refundAddress,
            {"from": st_sender},
        )

    # xSwapToken
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.xSwapToken(
            st_dstChain,
            st_dstAddress,
            st_dstToken,
            token,
            st_amount,
            {"from": st_sender},
        )


# xCallNative and xSwapNative


@given(
    st_dstChain=strategy("uint32"),
    st_dstAddress=strategy("bytes"),
    st_dstToken=strategy("uint16"),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", max_value=TEST_AMNT),
    st_dstNativeBudget=strategy("uint"),
    st_refundAddress=strategy("bytes"),
    st_sender=strategy("address"),
)
def test_swapETHAndCall(
    cf,
    st_sender,
    st_dstChain,
    st_dstAddress,
    st_dstToken,
    st_message,
    st_amount,
    st_dstNativeBudget,
    st_refundAddress,
):

    if st_amount == 0:
        with reverts(REV_MSG_NZ_UINT):
            cf.vault.xSwapNative(
                st_dstChain,
                st_dstAddress,
                st_dstToken,
                {"from": st_sender, "amount": st_amount},
            )

        with reverts(REV_MSG_NZ_UINT):
            cf.vault.xCallNative(
                st_dstChain,
                st_dstAddress,
                st_dstToken,
                st_message,
                st_dstNativeBudget,
                st_refundAddress,
                {"from": st_sender, "amount": st_amount},
            )

    else:
        # xSwapNative
        iniBal = web3.eth.get_balance(cf.vault.address)
        tx = cf.vault.xSwapNative(
            st_dstChain,
            st_dstAddress,
            st_dstToken,
            {"from": st_sender, "amount": st_amount},
        )
        assert web3.eth.get_balance(cf.vault.address) == iniBal + st_amount
        assert tx.events["SwapNative"][0].values() == [
            st_dstChain,
            hexStr(st_dstAddress),
            st_dstToken,
            st_amount,
            st_sender,
        ]

        # xCallNative
        iniBal = web3.eth.get_balance(cf.vault.address)

        tx = cf.vault.xCallNative(
            st_dstChain,
            st_dstAddress,
            st_dstToken,
            st_message,
            st_dstNativeBudget,
            st_refundAddress,
            {"from": st_sender, "amount": st_amount},
        )
        assert web3.eth.get_balance(cf.vault.address) == iniBal + st_amount
        assert tx.events["XCallNative"][0].values() == [
            st_dstChain,
            hexStr(st_dstAddress),
            st_dstToken,
            st_amount,
            st_sender,
            hexStr(st_message),
            st_dstNativeBudget,
            hexStr(st_refundAddress),
        ]


@given(
    st_dstChain=strategy("uint32"),
    st_dstAddress=strategy("bytes"),
    st_dstToken=strategy("uint16"),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_dstNativeBudget=strategy("uint"),
    st_refundAddress=strategy("bytes"),
    st_sender=strategy("address"),
)
def test_swapETHAndCall_rev_suspended(
    cf,
    st_sender,
    st_dstChain,
    st_dstAddress,
    st_dstToken,
    st_message,
    st_amount,
    st_dstNativeBudget,
    st_refundAddress,
):
    cf.vault.suspend({"from": cf.gov})

    # xCallNative
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.xCallNative(
            st_dstChain,
            st_dstAddress,
            st_dstToken,
            st_message,
            st_dstNativeBudget,
            st_refundAddress,
            {"from": st_sender, "amount": st_amount},
        )

    # xSwapNative
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.xSwapNative(
            st_dstChain,
            st_dstAddress,
            st_dstToken,
            {"from": st_sender, "amount": st_amount},
        )
