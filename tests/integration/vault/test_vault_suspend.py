from consts import *
from brownie import reverts
from brownie.test import given, strategy


@given(st_amount=strategy("uint"), st_reciever=strategy("address"))
def test_vault_suspend(cf, st_reciever, st_amount):

    # Suspend the Vault contract
    cf.vault.suspend({"from": cf.GOVERNOR})

    # allBatch
    callDataNoSig = cf.vault.allBatch.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        [JUNK_HEX],
        [ETH_ADDR],
        [ETH_ADDR],
        [NON_ZERO_ADDR],
        [TEST_AMNT],
    )

    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.allBatch(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            [JUNK_HEX],
            [ETH_ADDR],
            [ETH_ADDR],
            [NON_ZERO_ADDR],
            [TEST_AMNT],
        )

    # transfer
    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), ETH_ADDR, st_reciever, st_amount
    )
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.transfer(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            ETH_ADDR,
            st_reciever,
            st_amount,
        )

    # transferBatch
    callDataNoSig = cf.vault.transferBatch.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        [ETH_ADDR],
        [st_reciever],
        [st_amount],
    )
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.transferBatch(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            [ETH_ADDR],
            [st_reciever],
            [st_amount],
        )

    # fetchDepositEth
    callDataNoSig = cf.vault.fetchDepositEth.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), JUNK_HEX_PAD
    )
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.fetchDepositEth(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            JUNK_HEX_PAD,
        )

    # fetchDepositEthBatch
    callDataNoSig = cf.vault.fetchDepositEthBatch.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), [JUNK_HEX_PAD]
    )
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.fetchDepositEthBatch(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            [JUNK_HEX_PAD],
        )

    # fetchDepositToken
    callDataNoSig = cf.vault.fetchDepositToken.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), JUNK_HEX_PAD, ETH_ADDR
    )
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.fetchDepositToken(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            JUNK_HEX_PAD,
            ETH_ADDR,
        )

    # fetchDepositTokenBatch
    callDataNoSig = cf.vault.fetchDepositTokenBatch.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), [JUNK_HEX_PAD], [ETH_ADDR]
    )
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.fetchDepositTokenBatch(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            [JUNK_HEX_PAD],
            [ETH_ADDR],
        )
