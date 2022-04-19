from consts import *
from utils import *
from brownie import reverts
from brownie.test import given, strategy


@given(
    ethAmount=strategy("uint", max_value=INIT_ETH_BAL, min_value=TEST_AMNT),
    tokenAmount=strategy("uint", max_value=INIT_TOKEN_SUPPLY),
    token2Amount=strategy("uint", max_value=INIT_TOKEN_SUPPLY),
)
def test_govWithdraw(cf, token, token2, ethAmount, tokenAmount, token2Amount):
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

    with reverts(REV_MSG_VAULT_GOVERNOR):
        cf.vault.govWithdraw(tokenList, {"from": cf.ALICE})

    with reverts(REV_MSG_COMMUNITY_GUARD):
        cf.vault.govWithdraw(tokenList, {"from": cf.GOVERNOR})

    cf.vault.setCommunityGuard(DISABLE_COMMUNITY_GUARD, {"from": cf.COMMUNITY_KEY})

    with reverts(REV_MSG_VAULT_GOVERNOR):
        cf.vault.govWithdraw(tokenList, {"from": cf.ALICE})

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
