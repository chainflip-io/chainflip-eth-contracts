from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy


def test_constructor(cf, cfTester):
    assert cfTester.cfVault() == cf.vault.address


@given(
    st_srcChain=strategy("uint32"),
    st_srcAddress=strategy("bytes"),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_sender=strategy("address"),
    st_token=strategy("address"),
)
def test_rev_cfReceive_notVault(
    cf,
    cfTester,
    st_srcChain,
    st_srcAddress,
    st_message,
    st_amount,
    st_token,
    st_sender,
):
    ## st_sender will never be the vault
    with reverts(REV_MSG_CFREC_SENDER):
        cfTester.cfReceive(
            st_srcChain,
            st_srcAddress,
            st_message,
            st_token,
            st_amount,
            {"from": st_sender},
        )


@given(
    st_srcChain=strategy("uint32"),
    st_srcAddress=strategy("bytes"),
    st_message=strategy("bytes"),
    st_sender=strategy("address"),
)
def test_rev_cfReceivexCall_notVault(
    cf, cfTester, st_srcChain, st_srcAddress, st_message, st_sender
):
    ## st_sender will never be the vault
    with reverts(REV_MSG_CFREC_SENDER):
        cfTester.cfReceivexCall(
            st_srcChain, st_srcAddress, st_message, {"from": st_sender}
        )


@given(
    st_sender=strategy("address"),
    st_address=strategy("address"),
)
def test_rev_updateCfVault(cf, cfTester, st_sender, st_address):
    if st_sender != cf.SAFEKEEPER:
        ## only owner can update the cfVault address
        with reverts("CFReceiver: caller not owner"):
            cfTester.updateCfVault(st_address, {"from": st_sender})
    else:
        cfTester.updateCfVault(st_address, {"from": st_sender})
        assert cfTester.cfVault() == st_address
