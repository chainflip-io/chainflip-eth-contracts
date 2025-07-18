from consts import *
from brownie import reverts
from utils import *
from shared_tests import *
from brownie.convert.datatypes import HexString


def test_executexSwapAndCallNative_rev_sender(cf, cfScUtils):
    with reverts("ScUtils: caller not Cf Vault"):
        cfScUtils.cfReceive(
            1, "0x", "0x12", cf.flip.address, TEST_AMNT, {"from": cf.ALICE}
        )


def test_ccm_fund_vault_eth(cf, cfScUtils):

    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT)

    iniBalanceVault = web3.eth.get_balance(cf.vault.address)
    message = encode_abi(
        ["address", "bytes"], [cf.vault.address, bytes.fromhex(JUNK_HEX[2:])]
    )

    args = [
        [NATIVE_ADDR, cfScUtils.address, TEST_AMNT],
        1,
        "0x",
        message,
    ]
    tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    assert tx.events["FetchedNative"][0].values() == [cfScUtils.address, TEST_AMNT]
    assert tx.events["DepositToVaultAndScCall"][0].values() == [
        cf.vault.address,
        ZERO_ADDR,
        TEST_AMNT,
        NATIVE_ADDR,
        JUNK_HEX,
    ]

    assert web3.eth.get_balance(cf.vault.address) == iniBalanceVault


def test_ccm_fund_vault_flip(cf, cfScUtils, mockUSDT):

    tokens = [cf.flip, mockUSDT]
    amount = [TEST_AMNT, TEST_AMNT_USDC]

    for token, amount in zip(tokens, amount):
        token.transfer(cf.vault, amount, {"from": cf.SAFEKEEPER})

        iniBalanceVault = token.balanceOf(cf.vault)

        message = encode_abi(
            ["address", "bytes"], [cf.vault.address, bytes.fromhex(JUNK_HEX[2:])]
        )

        args = [
            [token.address, cfScUtils.address, amount],
            1,
            "0x",
            message,
        ]
        tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

        assert tx.events["DepositToVaultAndScCall"][0].values() == [
            cf.vault.address,
            ZERO_ADDR,
            amount,
            token.address,
            JUNK_HEX,
        ]
        assert token.balanceOf(cf.vault) == iniBalanceVault


def test_ccm_fund_rev_asset(cf, cfScUtils):
    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT)
    cf.flip.transfer(cf.vault, MIN_FUNDING, {"from": cf.SAFEKEEPER})

    message = encode_abi(
        ["address", "bytes"], [cfScUtils.address, bytes.fromhex(JUNK_HEX_PAD)]
    )

    args = [[NATIVE_ADDR, cfScUtils.address, TEST_AMNT], 1, "0x", message]
    with reverts("ScUtils: token not FLIP"):
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    args[3] = encode_abi(
        ["address", "bytes"],
        [cf.stateChainGateway.address, bytes.fromhex(JUNK_HEX_PAD)],
    )
    with reverts("ScUtils: token not FLIP"):
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)


def test_ccm_fund_scgateway(cf, cfScUtils):
    cf.flip.transfer(cf.vault, MIN_FUNDING, {"from": cf.SAFEKEEPER})

    iniBalanceVault = cf.flip.balanceOf(cf.vault)
    iniBalanceScGateway = cf.flip.balanceOf(cf.stateChainGateway)

    message = encode_abi(
        ["address", "bytes"], [cfScUtils.address, bytes.fromhex(JUNK_HEX_PAD)]
    )
    args = [
        [cf.flip.address, cfScUtils.address, MIN_FUNDING],
        1,
        "0x",
        message,
    ]
    tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    nodeId = tx.events["Funded"]["nodeID"]
    expectedNodeId = HexString(JUNK_HEX, "bytes32")
    assert nodeId == expectedNodeId

    assert tx.events["Funded"]["amount"] == MIN_FUNDING
    assert tx.events["Funded"]["funder"] == cfScUtils.address

    assert iniBalanceVault == cf.flip.balanceOf(cf.vault) + MIN_FUNDING
    assert iniBalanceScGateway == cf.flip.balanceOf(cf.stateChainGateway) - MIN_FUNDING


def test_ccm_fund_to(cf, cfScUtils, mockUSDT):
    toAddress = "0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511"

    tokens = [cf.flip, mockUSDT]
    amounts = [TEST_AMNT, TEST_AMNT_USDC]

    for token, amount in zip(tokens, amounts):

        token.transfer(cf.vault, amount, {"from": cf.SAFEKEEPER})

        iniVaultBalance = token.balanceOf(cf.vault)
        iniToAddressBalance = token.balanceOf(toAddress)

        message = encode_abi(
            ["address", "bytes"], [toAddress, bytes.fromhex(JUNK_HEX[2:])]
        )
        args = [
            [token.address, cfScUtils.address, amount],
            1,
            "0x",
            message,
        ]
        tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

        assert tx.events["DepositAndScCall"][0].values() == [
            cf.vault.address,
            ZERO_ADDR,
            amount,
            token.address,
            toAddress,
            JUNK_HEX,
        ]
        assert token.balanceOf(cf.vault) == iniVaultBalance - amount
        assert token.balanceOf(toAddress) == iniToAddressBalance + amount
