from consts import *
from brownie import reverts


def test_transfer_eth(cf):
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)

    startBalVault = cf.vault.balance()
    startBalRecipient = cf.ALICE.balance()

    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), ETH_ADDR, cf.ALICE, TEST_AMNT
    )
    cf.vault.transfer(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        ETH_ADDR,
        cf.ALICE,
        TEST_AMNT,
    )

    assert cf.vault.balance() - startBalVault == -TEST_AMNT
    assert cf.ALICE.balance() - startBalRecipient == TEST_AMNT


# token doesn't have a fallback function for receiving eth, so should fail
def test_transfer_eth_fails_recipient(cf, token):
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)

    startBalVault = cf.vault.balance()
    startBalRecipient = cf.ALICE.balance()

    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), ETH_ADDR, token, TEST_AMNT
    )
    tx = cf.vault.transfer(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        ETH_ADDR,
        token,
        TEST_AMNT,
    )

    assert tx.events["TransferFailed"][0].values() == [token, TEST_AMNT, web3.toHex(0)]
    assert cf.vault.balance() == startBalVault
    assert cf.ALICE.balance() == startBalRecipient


# Trying to send ETH when there's none in the Vault
def test_transfer_eth_fails_not_enough_eth(cf, token):
    startBalRecipient = cf.ALICE.balance()

    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        ETH_ADDR,
        cf.ALICE,
        TEST_AMNT,
    )
    tx = cf.vault.transfer(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        ETH_ADDR,
        cf.ALICE,
        TEST_AMNT,
    )

    assert tx.events["TransferFailed"][0].values() == [
        cf.ALICE,
        TEST_AMNT,
        web3.toHex(0),
    ]
    assert cf.vault.balance() == 0
    assert cf.ALICE.balance() == startBalRecipient


def test_transfer_token(cf, token):
    token.transfer(cf.vault, TEST_AMNT, {"from": cf.DEPLOYER})

    startBalVault = token.balanceOf(cf.vault)
    startBalRecipient = token.balanceOf(cf.ALICE)

    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), token, cf.ALICE, TEST_AMNT
    )
    cf.vault.transfer(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        token,
        cf.ALICE,
        TEST_AMNT,
    )

    assert token.balanceOf(cf.vault) - startBalVault == -TEST_AMNT
    assert token.balanceOf(cf.ALICE) - startBalRecipient == TEST_AMNT


def test_transfer_rev_tokenAddr(cf):
    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), ZERO_ADDR, cf.ALICE, TEST_AMNT
    )

    with reverts(REV_MSG_NZ_ADDR):
        cf.vault.transfer(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            ZERO_ADDR,
            cf.ALICE,
            TEST_AMNT,
        )


def test_transfer_rev_recipient(cf):
    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), ETH_ADDR, ZERO_ADDR, TEST_AMNT
    )

    with reverts(REV_MSG_NZ_ADDR):
        cf.vault.transfer(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            ETH_ADDR,
            ZERO_ADDR,
            TEST_AMNT,
        )


def test_transfer_rev_amount(cf):
    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), ETH_ADDR, cf.ALICE, 0
    )

    with reverts(REV_MSG_NZ_UINT):
        cf.vault.transfer(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            ETH_ADDR,
            cf.ALICE,
            0,
        )


def test_transfer_rev_msgHash(cf):
    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), ETH_ADDR, cf.ALICE, TEST_AMNT
    )
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[2] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.vault.transfer(sigData, ETH_ADDR, cf.ALICE, TEST_AMNT)


def test_transfer_rev_sig(cf):
    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), ETH_ADDR, cf.ALICE, TEST_AMNT
    )
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[3] += 1

    with reverts(REV_MSG_SIG):
        cf.vault.transfer(sigData, ETH_ADDR, cf.ALICE, TEST_AMNT)
