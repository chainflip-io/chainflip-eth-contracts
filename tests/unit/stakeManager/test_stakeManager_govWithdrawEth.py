from consts import *
from brownie import reverts
from brownie.test import given, strategy


def test_govWithdrawEth_rev(cf):
    with reverts(REV_MSG_GOV_GOVERNOR):
        cf.stakeManager.govWithdrawEth({"from": cf.ALICE})


def test_govWithdrawEth_zero(cf):
    # Initially there is no ETH in the contract
    assert cf.stakeManager.balance() == 0
    iniBalanceGovernor = cf.GOVERNOR.balance()

    # Withdraw amount is zero
    tx = cf.stakeManager.govWithdrawEth({"from": cf.GOVERNOR})

    assert cf.stakeManager.balance() == 0
    assert iniBalanceGovernor == cf.GOVERNOR.balance() + calculateGasTransaction(tx)


# Test that governance recovers all the ETH in the StakeManager contract
@given(st_ethAmount=strategy("uint", min_value=0, max_value=INIT_ETH_BAL))
def test_govWithdrawEth(cf, st_ethAmount):

    assert cf.stakeManager.balance() == 0

    # Using DENICE since it has INIT_ETH_BAL
    cf.DENICE.transfer(cf.stakeManager, st_ethAmount)

    iniBalanceContract = cf.stakeManager.balance()
    iniBalanceGovernor = cf.GOVERNOR.balance()

    assert iniBalanceContract == st_ethAmount

    # Withdraw amount
    tx = cf.stakeManager.govWithdrawEth({"from": cf.GOVERNOR})

    assert cf.stakeManager.balance() == 0
    assert (
        iniBalanceGovernor + st_ethAmount
        == cf.GOVERNOR.balance() + calculateGasTransaction(tx)
    )
