from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy


@given(
    st_sender=strategy("address"),
)
def test_executeActions_rev_erc20_max(cf, st_sender):
    function_call_bytes = cf.flip.transfer.encode_input(
        "0xf8e81D47203A594245E36C48e151709F0C19fBe8", 2**256 - 1
    )

    # Health check
    assert (
        function_call_bytes
        == "0xa9059cbb000000000000000000000000f8e81d47203a594245e36c48e151709f0c19fbe8ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    )

    with reverts("Vault: call failed"):
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            [[cf.flip, 0, function_call_bytes]],
            sender=st_sender,
        )


@given(
    st_sender=strategy("address"),
    st_ini_amount=strategy("uint256", max_value=TEST_AMNT * 10),
    st_amount=strategy("uint256", max_value=TEST_AMNT * 10),
    st_recipient=strategy("address"),
)
def test_executeActions_rev_erc20(
    cf, st_sender, st_ini_amount, st_amount, st_recipient
):
    assert cf.flip.balanceOf(cf.vault) == 0
    cf.flip.transfer(cf.vault, st_ini_amount, {"from": cf.SAFEKEEPER})
    iniBal_recipient = cf.flip.balanceOf(st_recipient)

    function_call_bytes = cf.flip.transfer.encode_input(st_recipient, st_amount)

    if st_amount > st_ini_amount:
        with reverts("Vault: call failed"):
            signed_call_cf(
                cf,
                cf.vault.executeActions,
                [[cf.flip, 0, function_call_bytes]],
                sender=st_sender,
            )
    else:
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            [[cf.flip, 0, function_call_bytes]],
            sender=st_sender,
        )
        assert cf.flip.balanceOf(cf.vault) == st_ini_amount - st_amount
        assert cf.flip.balanceOf(st_recipient) == iniBal_recipient + st_amount


@given(
    st_sender=strategy("address"),
    st_bytes=strategy("bytes"),
    st_uint=strategy("uint256"),
)
def test_executeActions_rev_vault(cf, st_sender, st_uint, st_bytes):
    with reverts("Vault: calling this contract"):
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            [[cf.vault.address, st_uint, st_bytes]],
            sender=st_sender,
        )


@given(
    st_sender=strategy("address"),
    st_srcChain=strategy("uint32"),
    st_srcAddress=strategy("bytes"),
    st_message=strategy("bytes"),
    st_token=strategy("address"),
    st_amount=strategy("uint256"),
)
def test_executeActions_rev_cfReceive(
    cf,
    st_sender,
    st_srcChain,
    st_srcAddress,
    st_message,
    st_token,
    st_amount,
    cfReceiverMock,
):
    function_call_bytes = cfReceiverMock.cfReceive.encode_input(
        st_srcChain, st_srcAddress, st_message, st_token, st_amount
    )
    with reverts("Vault: cfReceive not allowed"):
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            [[cfReceiverMock, 0, function_call_bytes]],
            sender=st_sender,
        )


## TODO: Add more tests for different executeActions scenarios
##       Try calling internal functions to ensure they are not callable
##       Check what happens if the bytes passed are <4
##       Check if we pass two actions with the first one being <4 bytes
##       Try interactions with Axelar/CCTP (Goerli?)
