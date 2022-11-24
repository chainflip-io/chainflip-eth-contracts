from consts import *
from brownie import reverts
from brownie.test import given, strategy

from shared_tests import *


@given(st_amount=strategy("uint", max_value=TEST_AMNT), st_reciever=strategy("address"))
def test_vault_suspend(cf, st_reciever, st_amount, token):

    # Suspend the Vault contract
    cf.vault.suspend({"from": cf.GOVERNOR})

    # allBatch
    with reverts(REV_MSG_GOV_SUSPENDED):
        fetchParams = craftFetchParamsArray([JUNK_HEX], [ETH_ADDR])
        transferParams = craftTransferParamsArray(
            [ETH_ADDR], [NON_ZERO_ADDR], [TEST_AMNT]
        )

        args = (fetchParams, transferParams)
        signed_call_cf(cf, cf.vault.allBatch, *args)

    # transfer
    with reverts(REV_MSG_GOV_SUSPENDED):
        signed_call_cf(cf, cf.vault.transfer, [ETH_ADDR, st_reciever, st_amount])

    # transferBatch
    with reverts(REV_MSG_GOV_SUSPENDED):
        args = [craftTransferParamsArray([ETH_ADDR], [st_reciever], [st_amount])]
        signed_call_cf(cf, cf.vault.transferBatch, *args)

    # fetchDepositEth
    with reverts(REV_MSG_GOV_SUSPENDED):
        signed_call_cf(cf, cf.vault.fetchDepositEth, JUNK_HEX_PAD)

    # fetchDepositEthBatch
    with reverts(REV_MSG_GOV_SUSPENDED):
        signed_call_cf(cf, cf.vault.fetchDepositEthBatch, [JUNK_HEX_PAD])

    # fetchDepositToken
    with reverts(REV_MSG_GOV_SUSPENDED):
        signed_call_cf(cf, cf.vault.fetchDepositToken, [JUNK_HEX_PAD, ETH_ADDR])

    # fetchDepositTokenBatch
    with reverts(REV_MSG_GOV_SUSPENDED):
        signed_call_cf(cf, cf.vault.fetchDepositTokenBatch, [[JUNK_HEX_PAD, ETH_ADDR]])

    # xSwapTokenAndCall
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.xSwapTokenAndCall(
            0,
            "dstAddress",
            "swapIntent",
            JUNK_HEX,
            token,
            st_amount,
            st_reciever,
        )

    # xSwapToken
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.xSwapToken(
            0,
            "dstAddress",
            "swapIntent",
            token,
            st_amount,
        )

    # xSwapNativeAndCall
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.xSwapNativeAndCall(
            0,
            "dstAddress",
            "swapIntent",
            JUNK_HEX,
            st_reciever,
            {"from": st_reciever, "amount": st_amount},
        )

    # xSwapNative
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.xSwapNative(
            0, "dstAddress", "swapIntent", {"from": st_reciever, "amount": st_amount}
        )

    # executexSwapAndCall
    with reverts(REV_MSG_GOV_SUSPENDED):
        transferParams = craftTransferParamsArray(
            [ETH_ADDR], [st_reciever], [st_amount]
        )
        signed_call_cf(
            cf,
            cf.vault.executexSwapAndCall,
            *transferParams,
            0,
            "anySrcAddress",
            JUNK_HEX
        )

    # executexCall
    with reverts(REV_MSG_GOV_SUSPENDED):
        signed_call_cf(
            cf, cf.vault.executexCall, st_reciever, 0, "anySrcAddress", JUNK_HEX
        )
