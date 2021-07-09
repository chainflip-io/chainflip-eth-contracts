from consts import *
from brownie import a, reverts


# This test takes advantage of Brownie's ability to send transactions from accounts that
# we don't have the private key for, like a contract, so this is impossible to do in reality,
# just to test the sending logic
def test_sendEth(cf):
    cf.DEPLOYER.transfer(cf.vault, 2*TEST_AMNT)

    assert cf.vault.balance() == 2*TEST_AMNT
    assert cf.DENICE.balance() == INIT_ETH_BAL

    cf.vault.sendEth(cf.DENICE, {'from': cf.vault, 'value': TEST_AMNT})

    assert cf.vault.balance() == TEST_AMNT
    assert cf.DENICE.balance() == INIT_ETH_BAL + TEST_AMNT


def test_sendEth_rev_sender(cf):
    cf.DEPLOYER.transfer(cf.vault, 2*TEST_AMNT)
    for addr in a:
        if addr != cf.vault.address:
            with reverts(REV_MSG_SENDER):
                cf.vault.sendEth(cf.DENICE, {'from': addr, 'value': TEST_AMNT})