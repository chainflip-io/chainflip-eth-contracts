from consts import *
from utils import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy


@given(st_sender=strategy("address"))
def test_govWithdraw_transfer(cf, token, token2, DepositEth, st_sender):
    # Funding Vault with some arbitrary funds
    amountTest = TEST_AMNT * 10
    st_sender.transfer(cf.vault, amountTest)
    token.transfer(cf.vault, amountTest, {"from": cf.DEPLOYER})
    token2.transfer(cf.vault, amountTest, {"from": cf.DEPLOYER})
    tokenList = [ETH_ADDR, token, token2]

    # Test vault functioning
    fetchDepositEth(cf, cf.vault, DepositEth)
    transfer_eth(cf, cf.vault, st_sender, TEST_AMNT)

    # Withdraw all Vault balance
    cf.vault.setCommunityGuard(DISABLE_COMMUNITY_GUARD, {"from": cf.COMMUNITY_KEY})

    cf.vault.govWithdraw(tokenList, {"from": cf.GOVERNOR})

    assert cf.vault.balance() == 0
    # Receiver balance do not change because no funds can be transferred
    minAmount = 1
    iniEthBal = st_sender.balance()
    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), ETH_ADDR, st_sender, minAmount
    )
    tx = cf.vault.transfer(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        ETH_ADDR,
        st_sender,
        minAmount,
        {"from": st_sender},
    )
    assert st_sender.balance() == iniEthBal - calculateGasTransaction(tx)

    # Vault can fetch still fetch amounts even after govWithdrawal - pending/old swaps
    fetchDepositEth(cf, cf.vault, DepositEth)
    # GovWithdraw amounts recently fetched
    iniEthBalGov = cf.GOVERNOR.balance()
    tx = cf.vault.govWithdraw([ETH_ADDR], {"from": cf.GOVERNOR})
    assert cf.GOVERNOR.balance() == iniEthBalGov + TEST_AMNT - calculateGasTransaction(
        tx
    )

    cf.vault.setCommunityGuard(ENABLE_COMMUNITY_GUARD, {"from": cf.COMMUNITY_KEY})

    fetchDepositEth(cf, cf.vault, DepositEth)
    # Governance cannot withdraw again since community Guard is enabled again
    with reverts(REV_MSG_COMMUNITY_GUARD):
        cf.vault.govWithdraw(tokenList, {"from": cf.GOVERNOR})

    # Vault has funds so it can transfer again
    transfer_eth(cf, cf.vault, st_sender, TEST_AMNT)
