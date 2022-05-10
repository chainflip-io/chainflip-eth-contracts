from consts import *
from utils import *
from brownie import reverts
from brownie.test import given, strategy


@given(
    ethAmount=strategy("uint", max_value=INIT_ETH_BAL, min_value=TEST_AMNT),
    tokenAmount=strategy("uint", max_value=INIT_TOKEN_SUPPLY),
    token2Amount=strategy("uint", max_value=INIT_TOKEN_SUPPLY),
    sleepTime=strategy("uint256", max_value=MONTH * 2),
)
def test_govWithdraw(
    cf, token, token2, ethAmount, tokenAmount, token2Amount, sleepTime
):

    # Fund Vault contract. Using non-deployer to transfer ETH because the deployer
    # doesn't have INIT_ETH_BAL - gas spent deploying contracts
    cf.DENICE.transfer(cf.vault, ethAmount)
    token.transfer(cf.vault, tokenAmount, {"from": cf.DEPLOYER})
    token2.transfer(cf.vault, token2Amount, {"from": cf.DEPLOYER})

    # Check Vault intial Balances
    assert cf.vault.balance() == ethAmount
    assert token.balanceOf(cf.vault) == tokenAmount
    assert token2.balanceOf(cf.vault) == token2Amount

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

    tokenList = [ETH_ADDR, token, token2]

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

    chain.sleep(sleepTime)
    if getChainTime() - cf.keyManager.getLastValidateTime() < AGG_KEY_EMERGENCY_TIMEOUT:
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
        ] + ethAmount - calculateGasSpentByAddress(cf.GOVERNOR, iniTransactionNumber[0])
        assert token.balanceOf(cf.GOVERNOR) == governorBalances[1] + tokenAmount
        assert token2.balanceOf(cf.GOVERNOR) == governorBalances[2] + token2Amount

        assert cf.COMMUNITY_KEY.balance() == communityBalances[
            0
        ] - calculateGasSpentByAddress(cf.COMMUNITY_KEY, iniTransactionNumber[1])
        assert token.balanceOf(cf.COMMUNITY_KEY) == communityBalances[1]
        assert token2.balanceOf(cf.COMMUNITY_KEY) == communityBalances[2]
