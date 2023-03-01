from brownie import reverts, web3
from brownie.test import given, strategy
from consts import *
from shared_tests import *


# addGasNative and addGasToken


@given(
    st_swapID=strategy("bytes32"),
    st_amount=strategy("uint", max_value=TEST_AMNT),
    st_sender=strategy("address"),
)
def test_addGas(cf, token, st_amount, st_sender, st_swapID):
    if st_amount == 0:
        with reverts(REV_MSG_NZ_UINT):
            cf.vault.addGasToken(
                st_swapID,
                st_amount,
                token,
                {"from": st_sender},
            )
        # AddGasNative shouldn't revert if amount is 0
        cf.vault.addGasNative(
            st_swapID,
            {"from": st_sender, "value": st_amount},
        )
    else:
        # Fund st_sender account
        token.transfer(st_sender, st_amount * 2)

        # addGasToken
        iniBalance = token.balanceOf(st_sender)
        iniBalanceVault = token.balanceOf(cf.vault)

        token.approve(cf.vault, st_amount, {"from": st_sender})
        tx = cf.vault.addGasToken(
            st_swapID,
            st_amount,
            token,
            {"from": st_sender},
        )
        assert token.balanceOf(st_sender) == iniBalance - st_amount
        assert token.balanceOf(cf.vault) == iniBalanceVault + st_amount
        assert tx.events["AddGasToken"][0].values() == [
            hexStr(st_swapID),
            st_amount,
            token,
        ]

        # addGasNative
        iniBalanceVault = web3.eth.get_balance(cf.vault.address)

        token.approve(cf.vault, st_amount, {"from": st_sender})
        tx = cf.vault.addGasNative(
            st_swapID,
            {"from": st_sender, "value": st_amount},
        )
        assert web3.eth.get_balance(cf.vault.address) == iniBalanceVault + st_amount
        assert tx.events["AddGasNative"][0].values() == [
            hexStr(st_swapID),
            st_amount,
        ]


@given(
    st_swapID=strategy("bytes32"),
    st_amount=strategy("uint", exclude=0),
    st_sender=strategy("address"),
)
def test_rev_zeroAddr(cf, st_amount, st_sender, st_swapID):
    with reverts("Address: call to non-contract"):
        cf.vault.addGasToken(
            st_swapID,
            st_amount,
            ZERO_ADDR,
            {"from": st_sender},
        )
