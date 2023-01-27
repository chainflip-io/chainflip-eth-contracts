from consts import *
from brownie import reverts
from brownie.test import given, strategy

from shared_tests import *


@given(st_amount=strategy("uint", max_value=TEST_AMNT), st_receiver=strategy("address"))
def test_vault_suspend(cf, st_receiver, st_amount, token):

    # Suspend the Vault contract
    cf.vault.suspend({"from": cf.GOVERNOR})

    deployFetchParamsArray = craftDeployFetchParamsArray([JUNK_HEX], [NATIVE_ADDR])
    fetchParamsArray = craftFetchParamsArray([NON_ZERO_ADDR], [NATIVE_ADDR])
    transferParamsArray = craftTransferParamsArray(
        [NATIVE_ADDR], [NON_ZERO_ADDR], [TEST_AMNT]
    )

    # allBatch
    with reverts(REV_MSG_GOV_SUSPENDED):
        args = (deployFetchParamsArray, fetchParamsArray, transferParamsArray)
        signed_call_cf(cf, cf.vault.allBatch, *args)

    # transfer
    with reverts(REV_MSG_GOV_SUSPENDED):
        signed_call_cf(cf, cf.vault.transfer, [NATIVE_ADDR, st_receiver, st_amount])

    # transferBatch
    with reverts(REV_MSG_GOV_SUSPENDED):
        args = [craftTransferParamsArray([NATIVE_ADDR], [st_receiver], [st_amount])]
        signed_call_cf(cf, cf.vault.transferBatch, *args)

    # fetchDepositNative
    with reverts(REV_MSG_GOV_SUSPENDED):
        signed_call_cf(cf, cf.vault.fetchBatch, fetchParamsArray)

    # deployAndFetchBatch
    with reverts(REV_MSG_GOV_SUSPENDED):
        signed_call_cf(cf, cf.vault.deployAndFetchBatch, deployFetchParamsArray)

    # xCallToken
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.xCallToken(
            0,
            "dstAddress",
            "swapIntent",
            JUNK_HEX,
            JUNK_INT,
            token,
            st_amount,
            st_receiver,
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

    # xCallNative
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.xCallNative(
            0,
            "dstAddress",
            "swapIntent",
            JUNK_HEX,
            JUNK_INT,
            st_receiver,
            {"from": st_receiver, "amount": st_amount},
        )

    # xSwapNative
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.xSwapNative(
            0, "dstAddress", "swapIntent", {"from": st_receiver, "amount": st_amount}
        )

    # executexSwapAndCall
    with reverts(REV_MSG_GOV_SUSPENDED):
        transferParams = craftTransferParamsArray(
            [NATIVE_ADDR], [st_receiver], [st_amount]
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
            cf, cf.vault.executexCall, st_receiver, 0, "anySrcAddress", JUNK_HEX
        )
