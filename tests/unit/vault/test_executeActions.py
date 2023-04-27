from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy
from brownie.convert import to_bytes


@given(
    st_sender=strategy("address"),
    st_multicall=strategy("address"),
)
def test_executeActions_rev_erc20_max(cf, st_sender, st_multicall):

    with reverts(REV_MSG_ERC20_EXCEED_BAL):
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            cf.flip,
            2**256 - 1,
            st_multicall,
            [[0, ZERO_ADDR, 0, JUNK_HEX, JUNK_HEX]],
            sender=st_sender,
        )


@given(
    st_sender=strategy("address"),
    st_ini_amount=strategy("uint256", max_value=TEST_AMNT * 10),
    st_amount=strategy("uint256", max_value=TEST_AMNT * 10),
    st_recipient=strategy("address"),
)
def test_executeActions_rev_erc20(
    cf, st_sender, multicall, st_ini_amount, st_amount, st_recipient
):
    assert cf.flip.balanceOf(cf.vault) == 0
    cf.flip.transfer(cf.vault, st_ini_amount, {"from": cf.SAFEKEEPER})
    iniBal_recipient = cf.flip.balanceOf(st_recipient)

    ## Just make another token transfer from multicall to st_recipient.
    call = [
        0,
        cf.flip.address,
        0,
        cf.flip.transfer.encode_input(st_recipient, st_amount),
        0,
    ]
    args = [cf.flip, st_amount, multicall, [call]]

    if st_amount > st_ini_amount:
        with reverts(REV_MSG_ERC20_EXCEED_BAL):
            signed_call_cf(
                cf,
                cf.vault.executeActions,
                *args,
                sender=st_sender,
            )
    else:
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            *args,
            sender=st_sender,
        )
        assert cf.flip.balanceOf(cf.vault) == st_ini_amount - st_amount
        assert cf.flip.balanceOf(st_recipient) == iniBal_recipient + st_amount


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
    multicall,
):
    ## Ensure we can't call a cfReceive or cfReceivexCall function via Multicall
    call = [
        0,
        cfReceiverMock,
        0,
        cfReceiverMock.cfReceive.encode_input(
            st_srcChain, st_srcAddress, st_message, st_token, st_amount
        ),
        0,
    ]
    args = [ZERO_ADDR, 0, multicall, [call]]

    ## It will revert with error CallFailed(uint256,bytes). Workaround since brownie
    ## doesn't support custom errors for now. It will be the same reason for both.
    bytes_revert_not_vault = (
        "typed error: "
        + web3.keccak(text="CallFailed(uint256,bytes)")[:4].hex()
        + "00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000008408c379a000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000027434652656365697665723a2063616c6c6572206e6f7420436861696e666c69702073656e6465720000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    )

    with reverts(bytes_revert_not_vault):
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            *args,
            sender=st_sender,
        )

    ## Ensure we can't call a cfReceive or cfReceivexCall function via Multicall
    call = [
        0,
        cfReceiverMock,
        0,
        cfReceiverMock.cfReceivexCall.encode_input(
            st_srcChain, st_srcAddress, st_message
        ),
        0,
    ]
    args = [ZERO_ADDR, 0, multicall, [call]]

    ## It will revert with error CallFailed(uint256,bytes). Workaround since brownie
    ## doesn't support custom errors for now.
    with reverts(bytes_revert_not_vault):
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            *args,
            sender=st_sender,
        )


@given(
    st_data=strategy("bytes"),
    st_receiver=strategy("address"),
    st_amount=strategy("uint256"),
    st_enum=strategy("uint256", max_value=3),
    st_sender=strategy("address"),
)
def test_executeActions_rev_length_eoa(
    cf, st_data, st_receiver, st_amount, st_enum, st_sender
):

    ## Ensure we can't call a cfReceive or cfReceivexCall function via Multicall
    call = [
        st_enum,
        st_receiver,
        st_amount,
        st_data,
        st_data,
    ]
    args = [ZERO_ADDR, 0, st_receiver, [call]]

    ## It will revert because it's calling an EOA.
    with reverts("Transaction reverted without a reason string"):
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            *args,
            sender=st_sender,
        )


@given(
    st_native_transfer=strategy("uint256", min_value=1, max_value=TEST_AMNT),
    st_native_vault=strategy("uint256", max_value=TEST_AMNT),
    st_sender=strategy("address"),
    st_bytes=strategy("bytes"),
)
def test_executeActions_rev_nativeBals(
    cf,
    st_native_transfer,
    st_native_vault,
    multicall,
    st_sender,
    st_bytes,
):
    # Just to make sure cf.ALICE != st_sender so we don't need to account for gas
    if st_sender == cf.ALICE:
        st_sender = cf.BOB

    # Assert initial native balances are zero
    assert web3.eth.get_balance(cf.vault.address) == 0
    assert web3.eth.get_balance(multicall.address) == 0

    cf.SAFEKEEPER.transfer(cf.vault.address, st_native_vault)

    ini_bals_multicall = 0
    ini_bals_vault = web3.eth.get_balance(cf.vault.address)
    ini_bals_alice = web3.eth.get_balance(cf.ALICE.address)

    ## Brownie has issues passing an empty bytes array so we just to a dummy
    ## call so the native tokens remain in the Multicall. An EOA can receive
    call = [
        0,
        cf.ALICE,
        st_native_transfer,
        st_bytes,
        st_bytes,
    ]

    args = [NATIVE_ADDR, st_native_transfer, multicall, [call]]

    if st_native_vault >= st_native_transfer:
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            *args,
            sender=st_sender,
        )
        assert (
            web3.eth.get_balance(cf.vault.address)
            == ini_bals_vault - st_native_transfer
        )
        assert web3.eth.get_balance(multicall.address) == 0
        assert (
            web3.eth.get_balance(cf.ALICE.address)
            == ini_bals_alice + st_native_transfer
        )
    else:
        with reverts("Transaction reverted without a reason string"):
            signed_call_cf(
                cf,
                cf.vault.executeActions,
                *args,
                sender=st_sender,
            )
        assert web3.eth.get_balance(multicall.address) == ini_bals_multicall
        assert web3.eth.get_balance(cf.vault.address) == ini_bals_vault
        assert web3.eth.get_balance(cf.ALICE.address) == ini_bals_alice


@given(
    st_token_transfer=strategy("uint256", min_value=1, max_value=TEST_AMNT),
    st_token_vault=strategy("uint256", max_value=TEST_AMNT),
    st_sender=strategy("address"),
    st_bytes=strategy("bytes"),
)
def test_executeActions_bridge_token(
    cf, st_token_transfer, st_token_vault, multicall, st_sender, st_bytes, token
):

    # Assert initial token balances are zero
    assert token.balanceOf(cf.vault.address) == 0
    assert token.balanceOf(multicall.address) == 0

    token.transfer(cf.vault.address, st_token_vault)

    ini_bals_multicall = 0
    ini_bals_vault = token.balanceOf(cf.vault.address)
    ini_bals_alice = token.balanceOf(cf.ALICE.address)

    call = [
        0,
        token,
        0,
        token.transfer.encode_input(cf.ALICE, st_token_transfer),
        st_bytes,
    ]

    args = [token, st_token_transfer, multicall, [call]]

    if st_token_vault >= st_token_transfer:
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            *args,
            sender=st_sender,
        )
        assert token.balanceOf(cf.vault.address) == ini_bals_vault - st_token_transfer
        assert token.balanceOf(multicall.address) == 0
        assert token.balanceOf(cf.ALICE.address) == ini_bals_alice + st_token_transfer
    else:
        with reverts(REV_MSG_ERC20_EXCEED_BAL):
            signed_call_cf(
                cf,
                cf.vault.executeActions,
                *args,
                sender=st_sender,
            )
        assert token.balanceOf(multicall.address) == ini_bals_multicall
        assert token.balanceOf(cf.vault.address) == ini_bals_vault
        assert token.balanceOf(cf.ALICE.address) == ini_bals_alice


## TODO: Try interactions with Axelar/CCTP (Goerli?) in intergration tests. Only to be run when
##       running a Goerli fork. This is already done as script in bridge_usdc.py but having some
##       tests would be nice.

# NOTE: Brownie is dumb and it can't make a bytes with zero length via strategy.
#       Even with min_size=0 and max_size=0 it will always generate a bytes of length 1.
#       So we have to manually generate the bytes with length 0 using b''.
#       However, doing that breaks the signature verification because Brownie has a bug
#       when encoding dynamic types with length zero.
# def test_executeActions_no_bytes(cf):
#     signed_call_cf(
#         cf,
#         cf.vault.executeActions,
#         [[cf.stateChainGateway, 0, b'']],
#     )

## TODO: TO update
# Workaround: manual signed call with an empty array to get around Brownie bugs/limitations
# def test_bytesZeroLength(cf):
#     args = [[cf.stateChainGateway, 0, b""]]
#     callDataNoSig = cf.vault.executeActions.encode_input(
#         agg_null_sig(cf.keyManager.address, chain.id), args
#     )
#     # Remove the last 32 bytes which are incorrect (length array == 0, therefore no value needs to follow it)
#     callDataNoSigModif = callDataNoSig[0 : len(callDataNoSig) - 32 * 2]

#     # If we end up removing the check for the calldata length, this call would not fail and instead transfer the
#     # native tokens to the stateChainGateway. This way we check the call has really zero calldata.
#     with reverts("Vault: must call contract/function"):
#         cf.vault.executeActions(
#             AGG_SIGNER_1.getSigData(callDataNoSigModif, cf.keyManager.address),
#             args,
#         )
