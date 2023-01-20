from consts import *
from brownie import reverts
from brownie.test import given, strategy


def test_govWithdrawNative_rev(cf):
    with reverts(REV_MSG_GOV_GOVERNOR):
        cf.stakeManager.govWithdrawNative({"from": cf.ALICE})


def test_govWithdrawNative_zero(cf):
    # Initially there is no native in the contract
    assert cf.stakeManager.balance() == 0
    iniBalanceGovernor = cf.GOVERNOR.balance()

    # Withdraw amount is zero
    tx = cf.stakeManager.govWithdrawNative({"from": cf.GOVERNOR})

    assert cf.stakeManager.balance() == 0
    assert iniBalanceGovernor == cf.GOVERNOR.balance() + calculateGasTransaction(tx)


# Test that governance recovers all the native in the StakeManager contract
@given(st_nativeAmount=strategy("uint", min_value=0, max_value=INIT_NATIVE_BAL))
def test_govWithdrawNative(cf, st_nativeAmount):

    assert cf.stakeManager.balance() == 0

    # Using DENICE since it has INIT_NATIVE_BAL
    cf.DENICE.transfer(cf.stakeManager, st_nativeAmount)

    iniBalanceContract = cf.stakeManager.balance()
    iniBalanceGovernor = cf.GOVERNOR.balance()

    assert iniBalanceContract == st_nativeAmount

    # Withdraw amount
    tx = cf.stakeManager.govWithdrawNative({"from": cf.GOVERNOR})

    assert cf.stakeManager.balance() == 0
    assert (
        iniBalanceGovernor + st_nativeAmount
        == cf.GOVERNOR.balance() + calculateGasTransaction(tx)
    )
