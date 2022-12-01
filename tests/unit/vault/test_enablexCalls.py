from brownie import reverts, web3
from brownie.test import given, strategy
from consts import *
from shared_tests import *


# Tests enable and disable swaps


@given(
    st_sender=strategy("address"),
)
def test_enablexCalls_rev_gov(cf, st_sender):
    assert cf.vault.getxCallsEnabled() == False
    if st_sender == cf.gov:
        cf.vault.enablexCalls({"from": st_sender})
        assert cf.vault.getxCallsEnabled() == True
    else:
        with reverts(REV_MSG_GOV_GOVERNOR):
            cf.vault.enablexCalls({"from": st_sender})
            assert cf.vault.getxCallsEnabled() == False


def test_enablexCalls_rev_enabled(cf):
    cf.vault.enablexCalls({"from": cf.gov})

    with reverts(REV_MSG_VAULT_SWAPS_EN):
        cf.vault.enablexCalls({"from": cf.gov})


@given(
    st_sender=strategy("address"),
)
def test_disablexCalls_rev_gov(cf, st_sender):
    assert cf.vault.getxCallsEnabled() == False
    cf.vault.enablexCalls({"from": cf.gov})
    assert cf.vault.getxCallsEnabled() == True
    if st_sender == cf.gov:
        cf.vault.disablexCalls({"from": st_sender})
        assert cf.vault.getxCallsEnabled() == False
    else:
        with reverts(REV_MSG_GOV_GOVERNOR):
            cf.vault.disablexCalls({"from": st_sender})
            assert cf.vault.getxCallsEnabled() == True


def test_enablexCalls_rev_disabled(cf):
    with reverts(REV_MSG_VAULT_XCALLS_DIS):
        cf.vault.disablexCalls({"from": cf.gov})
