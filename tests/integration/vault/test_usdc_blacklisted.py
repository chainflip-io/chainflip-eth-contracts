from consts import *
from shared_tests import *
from brownie import reverts


def test_transfer_usdc_exceed(cf, mockUsdc, utils):

    balVault = mockUsdc.balanceOf(cf.vault)

    args = [[mockUsdc.address, cf.ALICE, balVault + 1]]

    tx = signed_call_cf(cf, cf.vault.transfer, *args)
    assert tx.events["TransferTokenFailed"]["recipient"] == cf.ALICE
    assert tx.events["TransferTokenFailed"]["amount"] == balVault + 1
    assert tx.events["TransferTokenFailed"]["token"] == mockUsdc.address
    assert (
        utils.decodeRevertData(tx.events["TransferTokenFailed"]["reason"])
        == REV_MSG_ERC20_EXCEED_BAL
    )


def test_transfer_usdc(cf, mockUsdc):
    mockUsdc.transfer(cf.vault, TEST_AMNT_USDC, {"from": cf.SAFEKEEPER})

    startBalVault = mockUsdc.balanceOf(cf.vault)
    startBalRecipient = mockUsdc.balanceOf(cf.ALICE)

    args = [[mockUsdc.address, cf.ALICE, TEST_AMNT_USDC]]

    signed_call_cf(cf, cf.vault.transfer, *args)

    assert mockUsdc.balanceOf(cf.vault) - startBalVault == -TEST_AMNT_USDC
    assert mockUsdc.balanceOf(cf.ALICE) - startBalRecipient == TEST_AMNT_USDC


def test_transfer_blacklist_usdc(cf, mockUsdc, utils):
    mockUsdc.transfer(cf.vault, TEST_AMNT_USDC * 10, {"from": cf.SAFEKEEPER})

    inibal_native = cf.vault.balance()
    inibal_usdc = mockUsdc.balanceOf(cf.vault)

    ## Blacklist user
    mockUsdc.blacklist(cf.ALICE, {"from": cf.SAFEKEEPER})

    args = [[mockUsdc.address, cf.ALICE, TEST_AMNT_USDC]]
    tx = signed_call_cf(cf, cf.vault.transfer, *args)

    assert tx.events["TransferTokenFailed"]["recipient"] == cf.ALICE
    assert tx.events["TransferTokenFailed"]["amount"] == TEST_AMNT_USDC
    assert tx.events["TransferTokenFailed"]["token"] == mockUsdc.address
    assert (
        utils.decodeRevertData(tx.events["TransferTokenFailed"]["reason"])
        == "Blacklistable: account is blacklisted"
    )

    assert inibal_native == cf.vault.balance()
    assert inibal_usdc == mockUsdc.balanceOf(cf.vault)


## Check that a USDC blacklist would stop a batch
def test_transfer_blacklist_allbatch_usdc(cf, mockUsdc, token, utils):
    token.transfer(cf.vault, TEST_AMNT, {"from": cf.SAFEKEEPER})
    mockUsdc.transfer(cf.vault, TEST_AMNT_USDC, {"from": cf.SAFEKEEPER})

    inibal_native = cf.vault.balance()
    inibal_usdc = mockUsdc.balanceOf(cf.vault)

    ## Blacklist user
    mockUsdc.blacklist(cf.ALICE, {"from": cf.SAFEKEEPER})

    fetchParamsArray = []
    transferParams = [
        [token, cf.ALICE, TEST_AMNT],
        [mockUsdc.address, cf.ALICE, TEST_AMNT_USDC],
    ]

    args = [fetchParamsArray, transferParams]
    tx = signed_call_cf(cf, cf.vault.allBatch, *args)

    assert tx.events["TransferTokenFailed"]["recipient"] == cf.ALICE
    assert tx.events["TransferTokenFailed"]["amount"] == TEST_AMNT_USDC
    assert tx.events["TransferTokenFailed"]["token"] == mockUsdc.address
    assert (
        utils.decodeRevertData(tx.events["TransferTokenFailed"]["reason"])
        == "Blacklistable: account is blacklisted"
    )

    assert inibal_native == cf.vault.balance()
    assert inibal_usdc == mockUsdc.balanceOf(cf.vault)
