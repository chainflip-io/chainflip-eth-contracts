from brownie import reverts, web3
from brownie.test import given, strategy
from consts import *
from shared_tests import *


# Tests enable and disable swaps


@given(
    st_sender=strategy("address"),
)
def test_enableSwaps_rev_gov(cf, st_sender):
    assert cf.vault.getSwapsEnabled() == False
    if st_sender == cf.gov:
        cf.vault.enableSwaps({"from": st_sender})
        assert cf.vault.getSwapsEnabled() == True
    else:
        with reverts(REV_MSG_GOV_GOVERNOR):
            cf.vault.enableSwaps({"from": st_sender})
            assert cf.vault.getSwapsEnabled() == False


def test_enableSwaps_rev_enabled(cf):
    cf.vault.enableSwaps({"from": cf.gov})

    with reverts(REV_MSG_VAULT_SWAPS_EN):
        cf.vault.enableSwaps({"from": cf.gov})


@given(
    st_sender=strategy("address"),
)
def test_disableSwaps_rev_gov(cf, st_sender):
    assert cf.vault.getSwapsEnabled() == False
    cf.vault.enableSwaps({"from": cf.gov})
    assert cf.vault.getSwapsEnabled() == True
    if st_sender == cf.gov:
        cf.vault.disableSwaps({"from": st_sender})
        assert cf.vault.getSwapsEnabled() == False
    else:
        with reverts(REV_MSG_GOV_GOVERNOR):
            cf.vault.disableSwaps({"from": st_sender})
            assert cf.vault.getSwapsEnabled() == True


def test_enableSwaps_rev_disabled(cf):
    with reverts(REV_MSG_VAULT_SWAPS_DIS):
        cf.vault.disableSwaps({"from": cf.gov})
