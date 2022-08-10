from brownie import reverts, web3
from consts import *
from utils import *
from shared_tests import *


def test_fetchDepositToken(cf, token, DepositToken, **kwargs):
    amount = kwargs.get("amount", TEST_AMNT)

    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(
        cf.vault.address, JUNK_HEX_PAD, DepositToken, cleanHexStrPad(token.address)
    )

    assert token.balanceOf(cf.DEPLOYER) >= amount
    token.transfer(depositAddr, amount, {"from": cf.DEPLOYER})

    balanceVaultBefore = token.balanceOf(cf.vault)

    # Fetch the deposit
    signed_call_cf(cf, cf.vault.fetchDepositToken, [JUNK_HEX_PAD, token])

    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == balanceVaultBefore + amount

    return depositAddr


def test_fetchDepositToken_and_eth(cf, token, DepositToken):
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(
        cf.vault.address, JUNK_HEX_PAD, DepositToken, cleanHexStrPad(token.address)
    )
    token.transfer(depositAddr, TEST_AMNT, {"from": cf.DEPLOYER})
    cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)

    assert cf.vault.balance() == 0
    assert token.balanceOf(cf.vault) == 0

    # Fetch the deposit
    signed_call_cf(cf, cf.vault.fetchDepositToken, [JUNK_HEX_PAD, token])

    assert cf.vault.balance() == TEST_AMNT
    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == TEST_AMNT


def test_fetchDepositToken_rev_swapID(cf):
    with reverts(REV_MSG_NZ_BYTES32):
        signed_call_cf(cf, cf.vault.fetchDepositToken, ["", ETH_ADDR])


def test_fetchDepositToken_rev_tokenAddr(cf):
    with reverts(REV_MSG_NZ_ADDR):
        signed_call_cf(cf, cf.vault.fetchDepositToken, [JUNK_HEX_PAD, ZERO_ADDR])


def test_fetchDepositToken_rev_msgHash(cf):
    callDataNoSig = cf.vault.fetchDepositToken.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), [JUNK_HEX_PAD, ETH_ADDR]
    )

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[2] += 1
    # Fetch the deposit
    with reverts(REV_MSG_MSGHASH):
        cf.vault.fetchDepositToken(sigData, [JUNK_HEX_PAD, ETH_ADDR])


def test_fetchDepositToken_rev_sig(cf):
    callDataNoSig = cf.vault.fetchDepositToken.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), [JUNK_HEX_PAD, ETH_ADDR]
    )

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[3] += 1
    # Fetch the deposit
    with reverts(REV_MSG_SIG):
        cf.vault.fetchDepositToken(sigData, [JUNK_HEX_PAD, ETH_ADDR])


# Redeploy a DepositToken contract in the same address as the previous one. This is in case
# an attacker tries to grief the protocol by sending a small amount to an address where
# the CFE is expecting the user's input swap amount to be deposited. We need to then
# be able to redeploy the contract in the same address to be able to fetch the funds.
def test_fetchDepositToken_grief(cf, token, DepositToken):
    assert token.balanceOf(cf.vault) == 0

    addr0 = test_fetchDepositToken(cf, token, DepositToken)
    assert token.balanceOf(cf.vault) == TEST_AMNT

    addr1 = test_fetchDepositToken(cf, token, DepositToken, amount=TEST_AMNT * 200)
    assert token.balanceOf(cf.vault) == TEST_AMNT * (200 + 1)

    # Check addresses are the same
    assert addr0 == addr1
