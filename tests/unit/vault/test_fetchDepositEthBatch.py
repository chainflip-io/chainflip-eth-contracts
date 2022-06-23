from brownie import reverts, web3
from brownie.test import given, strategy
from consts import *
from utils import *
from shared_tests import *


@given(
    st_amounts=strategy("uint[]", max_value=TEST_AMNT),
    st_swapIDs=strategy("bytes32[]", unique=True),
)
def test_fetchDepositEthBatch(cf, DepositEth, st_amounts, st_swapIDs):
    trimToShortest([st_amounts, st_swapIDs])

    for am, id in zip(st_amounts, st_swapIDs):
        # Get the address to deposit to and deposit
        depositAddr = getCreate2Addr(cf.vault.address, id.hex(), DepositEth, "")
        cf.DEPLOYER.transfer(depositAddr, am)

    assert cf.vault.balance() == 0

    # Fetch the deposit
    signed_call_cf(cf, cf.vault.fetchDepositEthBatch, st_swapIDs, sender=cf.ALICE)

    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
    assert cf.vault.balance() == sum(st_amounts)


def test_fetchDepositEthBatch_rev_msgHash(cf):
    callDataNoSig = cf.vault.fetchDepositEthBatch.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), [JUNK_HEX_PAD]
    )

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[2] += 1
    # Fetch the deposit
    with reverts(REV_MSG_MSGHASH):
        cf.vault.fetchDepositEthBatch(sigData, [JUNK_HEX_PAD])


def test_fetchDepositEthBatch_rev_sig(cf):
    callDataNoSig = cf.vault.fetchDepositEthBatch.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), [JUNK_HEX_PAD]
    )

    sigData = AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address)
    sigData[3] += 1
    # Fetch the deposit
    with reverts(REV_MSG_SIG):
        cf.vault.fetchDepositEthBatch(sigData, [JUNK_HEX_PAD])
