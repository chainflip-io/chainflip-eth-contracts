from brownie import reverts, web3
from consts import *
from utils import *



def test_fetchDepositEth(cf, DepositEth):
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, JUNK_HEX_PAD, DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)

    assert cf.vault.balance() == ONE_ETH

    # Sign the tx without a msgHash or sig
    callDataNoSig = cf.vault.fetchDepositEth.encode_input(agg_null_sig(), JUNK_HEX_PAD)

    # Fetch the deposit
    balanceBefore = cf.ALICE.balance()
    tx = cf.vault.fetchDepositEth(AGG_SIGNER_1.getSigData(callDataNoSig), JUNK_HEX_PAD, cf.FR_ALICE)
    balanceAfter = cf.ALICE.balance()
    refunded = txRefundTest(balanceBefore, balanceAfter, tx)
    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
    assert cf.vault.balance() == ONE_ETH + TEST_AMNT - refunded


def test_fetchDepositEth_rev_swapID(cf):
    callDataNoSig = cf.vault.fetchDepositEth.encode_input(agg_null_sig(), "")

    with reverts(REV_MSG_NZ_BYTES32):
        cf.vault.fetchDepositEth(AGG_SIGNER_1.getSigData(callDataNoSig), "")



def test_fetchDepositEth_rev_msgHash(cf):
    callDataNoSig = cf.vault.fetchDepositEth.encode_input(agg_null_sig(), JUNK_HEX_PAD)

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[0] += 1
    # Fetch the deposit
    with reverts(REV_MSG_MSGHASH):
        cf.vault.fetchDepositEth(sigData, JUNK_HEX_PAD)


def test_fetchDepositEth_rev_sig(cf):
    callDataNoSig = cf.vault.fetchDepositEth.encode_input(agg_null_sig(), JUNK_HEX_PAD)

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[1] += 1
    # Fetch the deposit
    with reverts(REV_MSG_SIG):
        cf.vault.fetchDepositEth(sigData, JUNK_HEX_PAD)
