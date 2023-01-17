from consts import *
from brownie import a, reverts, web3
from utils import *
import pytest

# This test takes advantage of Brownie's ability to send transactions from accounts that
# we don't have the private key for, like a contract, so this is impossible to do in reality,
# just to test the sending logic.
# However, transactions sent from non-EOA accounts breaks brownie coverage - skip coverage
@pytest.mark.skip_coverage
def test_sendEth(cf):
    cf.DEPLOYER.transfer(cf.vault, 2 * TEST_AMNT)

    assert cf.vault.balance() == 2 * TEST_AMNT
    assert cf.DENICE.balance() == INIT_NATIVE_BAL

    tx = cf.vault.sendEth(cf.DENICE, {"from": cf.vault, "value": TEST_AMNT})
    # Since this test is spoofing access to the vault account, we also have to
    # account for the gas that was used by the tx when checking the balance
    nativeUsed = calculateGasTransaction(tx)

    assert cf.vault.balance() == TEST_AMNT - nativeUsed
    assert cf.DENICE.balance() == INIT_NATIVE_BAL + TEST_AMNT


def test_sendEth_rev_sender(cf):
    cf.DEPLOYER.transfer(cf.vault, 2 * TEST_AMNT)
    for addr in a:
        if addr != cf.vault.address:
            with reverts(REV_MSG_SENDER):
                cf.vault.sendEth(cf.DENICE, {"from": addr, "value": TEST_AMNT})
