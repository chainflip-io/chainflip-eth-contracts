from consts import *
from brownie import reverts
from brownie.test import given, strategy
from shared_tests import *


@given(st_amount=strategy("uint"), st_reciever=strategy("address"))
def test_vault_suspend(cf, st_reciever, st_amount):

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
        signed_call_cf(cf, cf.vault.transfer, [NATIVE_ADDR, st_reciever, st_amount])

    # transferBatch
    with reverts(REV_MSG_GOV_SUSPENDED):
        args = [craftTransferParamsArray([NATIVE_ADDR], [st_reciever], [st_amount])]
        signed_call_cf(cf, cf.vault.transferBatch, *args)

    # fetchDepositNative
    with reverts(REV_MSG_GOV_SUSPENDED):
        signed_call_cf(cf, cf.vault.fetchBatch, fetchParamsArray)

    # deployAndFetchBatch
    with reverts(REV_MSG_GOV_SUSPENDED):
        signed_call_cf(cf, cf.vault.deployAndFetchBatch, deployFetchParamsArray)

    # fetchBatch
    with reverts(REV_MSG_GOV_SUSPENDED):
        signed_call_cf(cf, cf.vault.fetchBatch, fetchParamsArray)
