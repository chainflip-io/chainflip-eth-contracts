from consts import *
from utils import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy


@given(st_sender=strategy("address"))
def test_govWithdraw_transfer(cf, token, token2, Deposit, st_sender):
    # Funding Vault with some arbitrary funds
    amountTest = TEST_AMNT * 10
    st_sender.transfer(cf.vault, amountTest)
    token.transfer(cf.vault, amountTest, {"from": cf.SAFEKEEPER})
    token2.transfer(cf.vault, amountTest, {"from": cf.SAFEKEEPER})
    tokenList = [NATIVE_ADDR, token, token2]

    # Test vault functioning
    depositAddr = deployAndFetchNative(cf, cf.vault, Deposit)
    transfer_native(cf, cf.vault, st_sender, TEST_AMNT)

    # Withdraw all Vault balance
    chain.sleep(AGG_KEY_EMERGENCY_TIMEOUT)
    cf.vault.suspend({"from": cf.GOVERNOR})
    cf.vault.disableCommunityGuard({"from": cf.COMMUNITY_KEY})
    cf.vault.govWithdraw(tokenList, {"from": cf.GOVERNOR})
    cf.vault.resume({"from": cf.GOVERNOR})

    assert cf.vault.balance() == 0
    # Receiver balance do not change because no funds can be transferred
    minAmount = 1
    iniEthBal = st_sender.balance()
    iniTransactionNumber = len(history.filter(sender=st_sender))

    args = [[NATIVE_ADDR, st_sender, minAmount]]
    signed_call_cf(cf, cf.vault.transfer, *args, sender=st_sender)

    assert st_sender.balance() == iniEthBal - calculateGasSpentByAddress(
        st_sender, iniTransactionNumber
    )

    # Vault can still fetch amounts even after govWithdrawal - pending/old swaps
    fetchToken(cf, cf.vault, depositAddr, token)
    cf.GOVERNOR.transfer(depositAddr, TEST_AMNT)
    # GovWithdraw amounts recently fetched
    chain.sleep(AGG_KEY_EMERGENCY_TIMEOUT)
    iniEthBalGov = cf.GOVERNOR.balance()
    iniTransactionNumber = len(history.filter(sender=cf.GOVERNOR))
    cf.vault.suspend({"from": cf.GOVERNOR})
    cf.vault.govWithdraw([NATIVE_ADDR], {"from": cf.GOVERNOR})
    cf.vault.resume({"from": cf.GOVERNOR})
    assert (
        cf.GOVERNOR.balance()
        == iniEthBalGov
        + TEST_AMNT
        - calculateGasSpentByAddress(cf.GOVERNOR, iniTransactionNumber)
    )

    cf.vault.enableCommunityGuard({"from": cf.COMMUNITY_KEY})

    fetchToken(cf, cf.vault, depositAddr, token)
    cf.GOVERNOR.transfer(depositAddr, TEST_AMNT)

    # Governance cannot withdraw again since community Guard is enabled again
    with reverts(REV_MSG_GOV_ENABLED_GUARD):
        cf.vault.govWithdraw(tokenList, {"from": cf.GOVERNOR})

    # Vault has funds so it can transfer again
    transfer_native(cf, cf.vault, st_sender, TEST_AMNT)
