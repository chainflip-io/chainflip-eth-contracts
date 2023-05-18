from consts import *
from utils import *
from brownie import reverts
from brownie.test import given, strategy
import random


@given(
    st_nativeAmount=strategy("uint", max_value=INIT_NATIVE_BAL, min_value=TEST_AMNT),
    st_tokenAmount=strategy("uint", max_value=INIT_TOKEN_SUPPLY),
    st_token2Amount=strategy("uint", max_value=INIT_TOKEN_SUPPLY),
)
def test_govWithdraw(
    cf, token, token2, st_nativeAmount, st_tokenAmount, st_token2Amount
):

    # Fund Vault contract. Using non-deployer to transfer native because the deployer
    # doesn't have INIT_NATIVE_BAL - gas spent deploying contracts
    cf.DENICE.transfer(cf.vault, st_nativeAmount)
    token.transfer(cf.vault, st_tokenAmount, {"from": cf.SAFEKEEPER})
    token2.transfer(cf.vault, st_token2Amount, {"from": cf.SAFEKEEPER})

    # Check Vault intial Balances
    assert cf.vault.balance() == st_nativeAmount
    assert token.balanceOf(cf.vault) == st_tokenAmount
    assert token2.balanceOf(cf.vault) == st_token2Amount

    governorBalances = [
        cf.GOVERNOR.balance(),
        token.balanceOf(cf.GOVERNOR),
        token2.balanceOf(cf.GOVERNOR),
    ]

    communityBalances = [
        cf.COMMUNITY_KEY.balance(),
        token.balanceOf(cf.COMMUNITY_KEY),
        token2.balanceOf(cf.COMMUNITY_KEY),
    ]

    iniTransactionNumber = [
        len(history.filter(sender=cf.GOVERNOR)),
        len(history.filter(sender=cf.COMMUNITY_KEY)),
    ]

    tokenList = [NATIVE_ADDR, token, token2]

    with reverts(REV_MSG_GOV_GOVERNOR):
        cf.vault.govWithdraw(tokenList, {"from": cf.ALICE})

    with reverts(REV_MSG_GOV_ENABLED_GUARD):
        cf.vault.govWithdraw(tokenList, {"from": cf.GOVERNOR})

    cf.vault.disableCommunityGuard({"from": cf.COMMUNITY_KEY})

    # Ensure that an external address cannot withdraw funds after removing guard
    with reverts(REV_MSG_GOV_GOVERNOR):
        cf.vault.govWithdraw(tokenList, {"from": cf.ALICE})

    with reverts(REV_MSG_GOV_NOT_SUSPENDED):
        cf.vault.govWithdraw(tokenList, {"from": cf.GOVERNOR})

    cf.vault.suspend({"from": cf.GOVERNOR})

    st_sleepTime = random.randint(
        AGG_KEY_EMERGENCY_TIMEOUT / 2, AGG_KEY_EMERGENCY_TIMEOUT * 2
    )

    chain.sleep(st_sleepTime)
    # Adding a time buffer because brownie is sometimes inconsistent with chain time in some cases
    if st_sleepTime == AGG_KEY_EMERGENCY_TIMEOUT / 2:

        with reverts(REV_MSG_VAULT_DELAY):
            cf.vault.govWithdraw(tokenList, {"from": cf.GOVERNOR})
    else:

        cf.vault.govWithdraw(tokenList, {"from": cf.GOVERNOR})

        # Ensure that the Vault is empty and all funds have been transferred to the governor (and none to the Community Key)
        assert cf.vault.balance() == 0
        assert token.balanceOf(cf.vault) == 0
        assert token2.balanceOf(cf.vault) == 0

        assert cf.GOVERNOR.balance() == governorBalances[
            0
        ] + st_nativeAmount - calculateGasSpentByAddress(
            cf.GOVERNOR, iniTransactionNumber[0]
        )
        assert token.balanceOf(cf.GOVERNOR) == governorBalances[1] + st_tokenAmount
        assert token2.balanceOf(cf.GOVERNOR) == governorBalances[2] + st_token2Amount

        assert cf.COMMUNITY_KEY.balance() == communityBalances[
            0
        ] - calculateGasSpentByAddress(cf.COMMUNITY_KEY, iniTransactionNumber[1])
        assert token.balanceOf(cf.COMMUNITY_KEY) == communityBalances[1]
        assert token2.balanceOf(cf.COMMUNITY_KEY) == communityBalances[2]
