from consts import *
from brownie import reverts
from utils import *
from shared_tests import *

scCall = "0x1234"


def test_deposit_rev_approve(cf, cfScUtils):
    with reverts(REV_MSG_ERC20_INSUF_ALLOW):
        cfScUtils.depositToScGateway(TEST_AMNT, "0x", {"from": cf.ALICE})
    with reverts(REV_MSG_ERC20_INSUF_ALLOW):
        cfScUtils.depositToVault(TEST_AMNT, cf.flip.address, "0x", {"from": cf.ALICE})
    with reverts(REV_MSG_ERC20_INSUF_ALLOW):
        cfScUtils.depositTo(
            TEST_AMNT, cf.flip.address, ZERO_ADDR, "0x", {"from": cf.ALICE}
        )


def test_deposit_scgateway(cf, cfScUtils):
    iniBalUser = cf.flip.balanceOf(cf.ALICE)
    iniBalScGateway = cf.flip.balanceOf(cf.stateChainGateway)
    iniBalScUtils = cf.flip.balanceOf(cfScUtils)
    cf.flip.approve(cfScUtils, TEST_AMNT, {"from": cf.ALICE})
    tx = cfScUtils.depositToScGateway(TEST_AMNT, scCall, {"from": cf.ALICE})
    assert tx.events["DepositToScGatewayAndScCall"]["amount"] == TEST_AMNT
    assert tx.events["DepositToScGatewayAndScCall"]["scCall"] == scCall
    assert tx.events["DepositToScGatewayAndScCall"]["sender"] == cf.ALICE
    assert tx.events["DepositToScGatewayAndScCall"]["signer"] == cf.ALICE

    assert cf.flip.balanceOf(cf.ALICE) == iniBalUser - TEST_AMNT
    assert cf.flip.balanceOf(cf.stateChainGateway) == iniBalScGateway + TEST_AMNT
    assert cf.flip.balanceOf(cfScUtils) == iniBalScUtils


def test_deposit_token_vault(cf, cfScUtils, mockUSDT):
    mockUSDT.transfer(cf.ALICE, TEST_AMNT_USDC, {"from": cf.SAFEKEEPER})

    tokens = [cf.flip, mockUSDT]
    amounts = [TEST_AMNT, TEST_AMNT_USDC]

    for token, amount in zip(tokens, amounts):
        iniBalUser = token.balanceOf(cf.ALICE)
        iniBalVault = token.balanceOf(cf.vault)
        iniBalScUtils = token.balanceOf(cfScUtils)
        token.approve(cfScUtils, amount, {"from": cf.ALICE})
        tx = cfScUtils.depositToVault(amount, token.address, scCall, {"from": cf.ALICE})
        assert tx.events["DepositToVaultAndScCall"]["amount"] == amount
        assert tx.events["DepositToVaultAndScCall"]["scCall"] == scCall
        assert tx.events["DepositToVaultAndScCall"]["sender"] == cf.ALICE
        assert tx.events["DepositToVaultAndScCall"]["signer"] == cf.ALICE

        assert token.balanceOf(cf.ALICE) == iniBalUser - amount
        assert token.balanceOf(cf.vault) == iniBalVault + amount
        assert token.balanceOf(cfScUtils) == iniBalScUtils


def test_deposit_eth_vault_rev_amount(cf, cfScUtils):
    with reverts("ScUtils: value missmatch"):
        cfScUtils.depositToVault(TEST_AMNT, NATIVE_ADDR, scCall, {"from": cf.ALICE})


def test_deposit_eth_vault(cf, cfScUtils):
    iniBalUser = cf.ALICE.balance()
    iniBalVault = cf.vault.balance()
    iniBalScUtils = cfScUtils.balance()

    tx = cfScUtils.depositToVault(
        TEST_AMNT, NATIVE_ADDR, scCall, {"from": cf.ALICE, "value": TEST_AMNT}
    )
    assert tx.events["DepositToVaultAndScCall"]["amount"] == TEST_AMNT
    assert tx.events["DepositToVaultAndScCall"]["scCall"] == scCall
    assert tx.events["DepositToVaultAndScCall"]["sender"] == cf.ALICE
    assert tx.events["DepositToVaultAndScCall"]["signer"] == cf.ALICE

    assert cf.ALICE.balance() < iniBalUser - TEST_AMNT
    assert cf.vault.balance() == iniBalVault + TEST_AMNT
    assert cfScUtils.balance() == iniBalScUtils


def test_deposit_eth_to_rev_amount(cf, cfScUtils):
    with reverts("ScUtils: value missmatch"):
        cfScUtils.depositTo(
            TEST_AMNT,
            NATIVE_ADDR,
            "0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511",
            scCall,
            {"from": cf.ALICE},
        )

    with reverts():
        cfScUtils.depositTo(
            TEST_AMNT,
            NATIVE_ADDR,
            cf.stateChainGateway.address,  # cant receive eth
            scCall,
            {"from": cf.ALICE, "value": TEST_AMNT},
        )


def test_deposit_token_to(cf, cfScUtils):
    toAddress = "0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511"
    iniBalUser = cf.flip.balanceOf(cf.ALICE)
    iniBalTo = cf.flip.balanceOf(toAddress)
    iniBalScUtils = cf.flip.balanceOf(cfScUtils)
    cf.flip.approve(cfScUtils, TEST_AMNT, {"from": cf.ALICE})
    tx = cfScUtils.depositTo(
        TEST_AMNT, cf.flip.address, toAddress, scCall, {"from": cf.ALICE}
    )
    assert tx.events["DepositAndScCall"]["amount"] == TEST_AMNT
    assert tx.events["DepositAndScCall"]["scCall"] == scCall
    assert tx.events["DepositAndScCall"]["sender"] == cf.ALICE
    assert tx.events["DepositAndScCall"]["to"] == toAddress
    assert tx.events["DepositAndScCall"]["signer"] == cf.ALICE

    assert cf.flip.balanceOf(cf.ALICE) == iniBalUser - TEST_AMNT
    assert cf.flip.balanceOf(toAddress) == iniBalTo + TEST_AMNT
    assert cf.flip.balanceOf(cfScUtils) == iniBalScUtils


def test_deposit_eth_to(cf, cfScUtils):
    iniBalUser = web3.eth.get_balance(cf.ALICE.address)
    iniBalScUtils = web3.eth.get_balance(cfScUtils.address)
    iniBalTo = web3.eth.get_balance(NON_ZERO_ADDR)

    tx = cfScUtils.depositTo(
        TEST_AMNT,
        NATIVE_ADDR,
        NON_ZERO_ADDR,
        scCall,
        {"from": cf.ALICE, "value": TEST_AMNT},
    )
    assert tx.events["DepositAndScCall"]["amount"] == TEST_AMNT
    assert tx.events["DepositAndScCall"]["scCall"] == scCall
    assert tx.events["DepositAndScCall"]["sender"] == cf.ALICE
    assert tx.events["DepositAndScCall"]["to"] == NON_ZERO_ADDR
    assert tx.events["DepositAndScCall"]["signer"] == cf.ALICE

    assert web3.eth.get_balance(cf.ALICE.address) < iniBalUser - TEST_AMNT
    assert web3.eth.get_balance(NON_ZERO_ADDR) == iniBalTo + TEST_AMNT
    assert web3.eth.get_balance(cfScUtils.address) == iniBalScUtils


def test_call_sc(cf, cfScUtils):
    tx = cfScUtils.callSc(scCall, {"from": cf.ALICE})
    assert tx.events["CallSc"]["scCall"] == scCall
    assert tx.events["CallSc"]["sender"] == cf.ALICE
    assert tx.events["CallSc"]["signer"] == cf.ALICE
