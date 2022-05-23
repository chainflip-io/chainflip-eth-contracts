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
        args = (
            [JUNK_HEX],
            [ETH_ADDR],
            [ETH_ADDR],
            [NON_ZERO_ADDR],
            [TEST_AMNT],
        )
        signed_call_aggSigner(cf, cf.vault.allBatch, *args)

    # transfer
    with reverts(REV_MSG_GOV_SUSPENDED):
        args = (ETH_ADDR, st_reciever, st_amount)
        signed_call_aggSigner(cf, cf.vault.transfer, *args)

    # transferBatch
    with reverts(REV_MSG_GOV_SUSPENDED):
        args = (
            [ETH_ADDR],
            [st_reciever],
            [st_amount],
        )
        signed_call_aggSigner(cf, cf.vault.transferBatch, *args)

    # fetchDepositEth
    with reverts(REV_MSG_GOV_SUSPENDED):
        signed_call_aggSigner(cf, cf.vault.fetchDepositEth, JUNK_HEX_PAD)

    # fetchDepositEthBatch
    with reverts(REV_MSG_GOV_SUSPENDED):
        signed_call_aggSigner(cf, cf.vault.fetchDepositEthBatch, [JUNK_HEX_PAD])

    # fetchDepositToken
    with reverts(REV_MSG_GOV_SUSPENDED):
        args = (JUNK_HEX_PAD, ETH_ADDR)
        signed_call_aggSigner(cf, cf.vault.fetchDepositToken, *args)

    # fetchDepositTokenBatch
    with reverts(REV_MSG_GOV_SUSPENDED):
        args = ([JUNK_HEX_PAD], [ETH_ADDR])
        signed_call_aggSigner(cf, cf.vault.fetchDepositTokenBatch, *args)
