from brownie import reverts, web3
from brownie.test import given, strategy
from consts import *
from utils import *


@given(
    amounts=strategy('uint[]', max_value=TEST_AMNT),
    swapIDs=strategy('bytes32[]', unique=True)
)
def test_fetchDepositEthBatch(cf, DepositEth, amounts, swapIDs):
    trimToShortest([amounts, swapIDs])


    for am, id in zip(amounts, swapIDs):
        # Get the address to deposit to and deposit
        depositAddr = getCreate2Addr(cf.vault.address, id.hex(), DepositEth, "")
        cf.DEPLOYER.transfer(depositAddr, am)

    assert cf.vault.balance() == ONE_ETH

    # Sign the tx without a msgHash or sig
    callDataNoSig = cf.vault.fetchDepositEthBatch.encode_input(agg_null_sig(), swapIDs)

    # Fetch the deposit
    balanceBefore = cf.ALICE.balance()
    tx = cf.vault.fetchDepositEthBatch(AGG_SIGNER_1.getSigData(callDataNoSig), swapIDs, cf.FR_ALICE)
    balanceAfter = cf.ALICE.balance()
    refunded = txRefundTest(balanceBefore, balanceAfter, tx)

    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
    assert cf.vault.balance() == sum(amounts) + ONE_ETH - refunded


def test_fetchDepositEthBatch_rev_msgHash(cf):
    callDataNoSig = cf.vault.fetchDepositEthBatch.encode_input(agg_null_sig(), [JUNK_HEX_PAD])

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[0] += 1
    # Fetch the deposit
    with reverts(REV_MSG_MSGHASH):
        cf.vault.fetchDepositEthBatch(sigData, [JUNK_HEX_PAD])


def test_fetchDepositEthBatch_rev_sig(cf):
    callDataNoSig = cf.vault.fetchDepositEthBatch.encode_input(agg_null_sig(), [JUNK_HEX_PAD])

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[1] += 1
    # Fetch the deposit
    with reverts(REV_MSG_SIG):
        cf.vault.fetchDepositEthBatch(sigData, [JUNK_HEX_PAD])