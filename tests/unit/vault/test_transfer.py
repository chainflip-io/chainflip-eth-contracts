from consts import *
from brownie import reverts


def test_transfer_eth(cf, chain):
    cf.DEPLOYER.transfer(cf.vault, TEST_AMNT)

    startBalVault = cf.vault.balance()
    startBalRecipient = cf.ALICE.balance()
    
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, cf.ALICE, TEST_AMNT)
    cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, TEST_AMNT)
    
    assert cf.vault.balance() - startBalVault == -TEST_AMNT
    assert cf.ALICE.balance() - startBalRecipient == TEST_AMNT


def test_transfer_token(cf, token):
    token.transfer(cf.vault, TEST_AMNT, {'from': cf.DEPLOYER})

    startBalVault = token.balanceOf(cf.vault)
    startBalRecipient = token.balanceOf(cf.ALICE)

    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, token, cf.ALICE, TEST_AMNT)
    cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), token, cf.ALICE, TEST_AMNT)
    
    assert token.balanceOf(cf.vault) - startBalVault == -TEST_AMNT
    assert token.balanceOf(cf.ALICE) - startBalRecipient == TEST_AMNT


def test_transfer_rev_tokenAddr(cf):
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ZERO_ADDR, cf.ALICE, TEST_AMNT)

    with reverts(REV_MSG_NZ_ADDR):
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ZERO_ADDR, cf.ALICE, TEST_AMNT)


def test_transfer_rev_recipient(cf):
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, ZERO_ADDR, TEST_AMNT)

    with reverts(REV_MSG_NZ_ADDR):
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, ZERO_ADDR, TEST_AMNT)


def test_transfer_rev_amount(cf):
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, cf.ALICE, 0)

    with reverts(REV_MSG_NZ_UINT):
        cf.vault.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), ETH_ADDR, cf.ALICE, 0)


def test_transfer_rev_msgHash(cf):
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, cf.ALICE, TEST_AMNT)
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[0] += 1

    with reverts(REV_MSG_MSGHASH):
        cf.vault.transfer(sigData, ETH_ADDR, cf.ALICE, TEST_AMNT)


def test_transfer_rev_sig(cf):
    callDataNoSig = cf.vault.transfer.encode_input(NULL_SIG_DATA, ETH_ADDR, cf.ALICE, TEST_AMNT)
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[1] += 1

    with reverts(REV_MSG_SIG):
        cf.vault.transfer(sigData, ETH_ADDR, cf.ALICE, TEST_AMNT)