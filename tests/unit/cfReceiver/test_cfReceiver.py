from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy


def test_constructor(cf, cfReceiverMock):
    assert cfReceiverMock._cfSender() == cf.vault.address


@given(
    st_srcChain=strategy("uint32"),
    st_srcAddress=strategy("string", min_size=1),
    st_message=strategy("bytes"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
    st_sender=strategy("address"),
    st_token=strategy("address"),
)
def test_rev_cfRecieve_notVault(
    cf,
    cfReceiverMock,
    st_srcChain,
    st_srcAddress,
    st_message,
    st_amount,
    st_token,
    st_sender,
):
    ## st_sender will never be the vault
    with reverts(REV_MSG_SENDER):
        cfReceiverMock.cfRecieve(
            st_srcChain,
            st_srcAddress,
            st_message,
            st_token,
            st_amount,
            {"from": st_sender},
        )


@given(
    st_srcChain=strategy("uint32"),
    st_srcAddress=strategy("string", min_size=1),
    st_message=strategy("bytes"),
    st_sender=strategy("address"),
)
def test_rev_cfRecievexCall_notVault(
    cf, cfReceiverMock, st_srcChain, st_srcAddress, st_message, st_sender
):
    ## st_sender will never be the vault
    with reverts(REV_MSG_SENDER):
        cfReceiverMock.cfRecievexCall(
            st_srcChain, st_srcAddress, st_message, {"from": st_sender}
        )