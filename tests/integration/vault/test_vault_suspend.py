from consts import *
from brownie import reverts
from brownie.test import given, strategy
from shared_tests import *


@given(st_amount=strategy("uint"), st_reciever=strategy("address"))
def test_vault_suspend(cf, st_reciever, st_amount):

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
