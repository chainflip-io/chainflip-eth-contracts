from brownie import reverts, web3
from consts import *
from utils import *


def test_fetchDepositToken(cf, token, DepositToken):
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(
        cf.vault.address, JUNK_HEX_PAD, DepositToken, cleanHexStrPad(token.address)
    )
    token.transfer(depositAddr, TEST_AMNT, {"from": cf.DEPLOYER})

    assert token.balanceOf(cf.vault) == 0

    # Sign the tx without a msgHash or sig
    callDataNoSig = cf.vault.fetchDepositToken.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), JUNK_HEX_PAD, token
    )

    # Fetch the deposit
    cf.vault.fetchDepositToken(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        JUNK_HEX_PAD,
        token,
    )

    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == TEST_AMNT


def test_fetchDepositToken_and_eth(cf, token, DepositToken):
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(
        cf.vault.address, JUNK_HEX_PAD, DepositToken, cleanHexStrPad(token.address)
    )
    token.transfer(depositAddr, TEST_AMNT, {"from": cf.DEPLOYER})
    cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)

    assert cf.vault.balance() == 0
    assert token.balanceOf(cf.vault) == 0

    # Sign the tx without a msgHash or sig
    callDataNoSig = cf.vault.fetchDepositToken.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), JUNK_HEX_PAD, token
    )

    # Fetch the deposit
    balanceBefore = cf.ALICE.balance()
    tx = cf.vault.fetchDepositToken(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        JUNK_HEX_PAD,
        token,
        cf.FR_ALICE,
    )
    balanceAfter = cf.ALICE.balance()

    assert cf.vault.balance() == TEST_AMNT
    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == TEST_AMNT


def test_fetchDepositToken_rev_swapID(cf):
    callDataNoSig = cf.vault.fetchDepositToken.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), "", ETH_ADDR
    )

    with reverts(REV_MSG_NZ_BYTES32):
        cf.vault.fetchDepositToken(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), "", ETH_ADDR
        )


def test_fetchDepositToken_rev_tokenAddr(cf):
    callDataNoSig = cf.vault.fetchDepositToken.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), JUNK_HEX_PAD, ZERO_ADDR
    )

    with reverts(REV_MSG_NZ_ADDR):
        cf.vault.fetchDepositToken(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            JUNK_HEX_PAD,
            ZERO_ADDR,
        )


def test_fetchDepositToken_rev_msgHash(cf):
    callDataNoSig = cf.vault.fetchDepositToken.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), JUNK_HEX_PAD, ETH_ADDR
    )

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[2] += 1
    # Fetch the deposit
    with reverts(REV_MSG_MSGHASH):
        cf.vault.fetchDepositToken(sigData, JUNK_HEX_PAD, ETH_ADDR)


def test_fetchDepositToken_rev_sig(cf):
    callDataNoSig = cf.vault.fetchDepositToken.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), JUNK_HEX_PAD, ETH_ADDR
    )

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[3] += 1
    # Fetch the deposit
    with reverts(REV_MSG_SIG):
        cf.vault.fetchDepositToken(sigData, JUNK_HEX_PAD, ETH_ADDR)
