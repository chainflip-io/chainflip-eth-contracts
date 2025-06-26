from consts import *
from brownie import reverts
from utils import *
from shared_tests import *
from brownie.convert.datatypes import HexString


def test_executexSwapAndCallNative_rev_sender(cf, cfScUtils):
    with reverts("ScUtils: caller not Chainflip Vault"):
        cfScUtils.cfReceive(
            1, "0x", "0x12", cf.flip.address, TEST_AMNT, {"from": cf.ALICE}
        )


def test_ccm_fund_vault_eth(cf, cfScUtils):
    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT)
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
        TEST_AMNT,
        NATIVE_ADDR,
        JUNK_HEX,
    ]


def test_ccm_fund_vault_flip(cf, cfScUtils):
    cf.flip.transfer(cf.vault, TEST_AMNT, {"from": cf.SAFEKEEPER})

    iniBalanceVault = cf.flip.balanceOf(cf.vault)

    message = encode_abi(
        ["address", "bytes"], [cf.vault.address, bytes.fromhex(JUNK_HEX[2:])]
    )

    args = [
        [cf.flip.address, cfScUtils.address, TEST_AMNT],
        1,
        "0x",
        message,
    ]
    tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    assert tx.events["DepositToVaultAndScCall"][0].values() == [
        cf.vault.address,
        TEST_AMNT,
        cf.flip.address,
        JUNK_HEX,
    ]
    assert cf.flip.balanceOf(cf.vault) == iniBalanceVault


def test_ccm_fund_rev_asset(cf, cfScUtils):
    cf.SAFEKEEPER.transfer(cf.vault, TEST_AMNT)
    cf.flip.transfer(cf.vault, MIN_FUNDING, {"from": cf.SAFEKEEPER})

    message = encode_abi(
        ["address", "bytes"], [cfScUtils.address, bytes.fromhex(JUNK_HEX_PAD)]
    )

    args = [[NATIVE_ADDR, cfScUtils.address, TEST_AMNT], 1, "0x", message]
    with reverts("ScUtils: token is not FLIP"):
        signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    args[3] = encode_abi(
        ["address", "bytes"],
        [cf.stateChainGateway.address, bytes.fromhex(JUNK_HEX_PAD)],
    )
    with reverts("ScUtils: token is not FLIP"):
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


def test_ccm_fund_to(cf, cfScUtils):
    toAddress = "0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511"

    cf.flip.transfer(cf.vault, TEST_AMNT, {"from": cf.SAFEKEEPER})

    message = encode_abi(["address", "bytes"], [toAddress, bytes.fromhex(JUNK_HEX[2:])])
    args = [
        [cf.flip.address, cfScUtils.address, TEST_AMNT],
        1,
        "0x",
        message,
    ]
    tx = signed_call_cf(cf, cf.vault.executexSwapAndCall, *args)

    assert tx.events["DepositAndScCall"][0].values() == [
        cf.vault.address,
        TEST_AMNT,
        cf.flip.address,
        toAddress,
        JUNK_HEX,
    ]
