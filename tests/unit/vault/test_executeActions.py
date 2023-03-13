from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy
from brownie.convert import to_bytes


@given(
    st_sender=strategy("address"),
)
def test_executeActions_rev_erc20_max(cf, st_sender, utils):
    calldata = cf.flip.transfer.encode_input(
        "0xf8e81D47203A594245E36C48e151709F0C19fBe8", 2**256 - 1
    )

    # Health check
    assert (
        calldata
        == "0xa9059cbb000000000000000000000000f8e81d47203a594245e36c48e151709f0c19fbe8ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    )

    with reverts(REV_MSG_ERC20_EXCEED_BAL):
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            [[cf.flip, 0, calldata]],
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

    calldata = cf.flip.transfer.encode_input(st_recipient, st_amount)

    if st_amount > st_ini_amount:
        with reverts(REV_MSG_ERC20_EXCEED_BAL):
            signed_call_cf(
                cf,
                cf.vault.executeActions,
                [[cf.flip, 0, calldata]],
                sender=st_sender,
            )
    else:
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            [[cf.flip, 0, calldata]],
            sender=st_sender,
        )
        assert cf.flip.balanceOf(cf.vault) == st_ini_amount - st_amount
        assert cf.flip.balanceOf(st_recipient) == iniBal_recipient + st_amount


@given(
    st_sender=strategy("address"),
    st_bytes=strategy("bytes", min_size=4),
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
    calldata = cfReceiverMock.cfReceive.encode_input(
        st_srcChain, st_srcAddress, st_message, st_token, st_amount
    )
    with reverts("Vault: cfReceive not allowed"):
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            [[cfReceiverMock, 0, calldata]],
            sender=st_sender,
        )


@given(
    st_sender=strategy("address"),
    st_srcChain=strategy("uint32"),
    st_srcAddress=strategy("bytes"),
    st_message=strategy("bytes"),
)
def test_executeActions_rev_cfReceivexCall(
    cf,
    st_sender,
    st_srcChain,
    st_srcAddress,
    st_message,
    cfReceiverMock,
):
    calldata = cfReceiverMock.cfReceivexCall.encode_input(
        st_srcChain, st_srcAddress, st_message
    )
    with reverts("Vault: cfReceive not allowed"):
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            [[cfReceiverMock, 0, calldata]],
            sender=st_sender,
        )


# NOTE: Brownie is dumb and it can't make a bytes with zero length via strategy.
#       Even with min_size=0 and max_size=0 it will always generate a bytes of length 1.
#       So we have to manually generate the bytes with length 0 using b''.
#       However, doing that breaks the signature verification for some reason.
#       It reverts with: KeyManager: invalid msgHash. Probably the encode_input is also
#       suffering from the same issue.
# def test_executeActions_no_bytes(cf):
#     signed_call_cf(
#         cf,
#         cf.vault.executeActions,
#         [[cf.stakeManager, 0, b'']],
#     )


# Workaround: manual signed call with an empty array to get around Brownie bugs/limitations
def test_bytesZeroLength(cf):
    args = [[cf.stakeManager, 0, b""]]
    callDataNoSig = cf.vault.executeActions.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), args
    )
    # Remove the last 32 bytes which are incorrect (length array == 0, therefore no value needs to follow it)
    callDataNoSigModif = callDataNoSig[0 : len(callDataNoSig) - 32 * 2]

    # If we end up removing the check for the calldata length, this call would not fail and instead transfer the
    # native tokens to the stakeManager. This way we check the call has really zero calldata.
    with reverts("Vault: must call contract/function"):
        cf.vault.executeActions(
            AGG_SIGNER_1.getSigData(callDataNoSigModif, cf.keyManager.address),
            args,
        )


@given(
    st_sender=strategy("address"),
    st_native_amount=strategy("uint256"),
)
def test_executeActions_cfRecieve_onlySelector(
    cf, cfReceiverMock, st_native_amount, st_sender
):
    # Selector == 4 bytes + "0x" + dummy bits Brownie = 0:10
    encoded_call = cfReceiverMock.cfReceivexCall.encode_input(
        JUNK_INT, JUNK_HEX, JUNK_HEX
    )
    function_selector = encoded_call[0:10]
    with reverts("Vault: cfReceive not allowed"):
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            [[cfReceiverMock, st_native_amount, function_selector]],
            sender=st_sender,
        )

    encoded_call = cfReceiverMock.cfReceive.encode_input(
        JUNK_INT, JUNK_HEX, JUNK_HEX, NON_ZERO_ADDR, JUNK_INT
    )
    function_selector = encoded_call[0:10]
    with reverts("Vault: cfReceive not allowed"):
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            [[cfReceiverMock, st_native_amount, function_selector]],
            sender=st_sender,
        )


@given(
    st_data=strategy("bytes"),
    st_receiver=strategy("address"),
)
def test_executeActions_rev_length_eoa(cf, st_data, st_receiver):
    if len(st_data) > 0 and len(st_data) < 4:
        with reverts("Vault: must call contract/function"):
            signed_call_cf(
                cf,
                cf.vault.executeActions,
                [[st_receiver, 0, st_data]],
            )
    else:
        # We assume the st_data won't exactly hit one of the KeyManager selectors and
        # with the exact parameters expected. If it does, then the test will fail.
        with reverts("Transaction reverted without a reason string"):
            signed_call_cf(
                cf,
                cf.vault.executeActions,
                [[cf.keyManager, 0, st_data]],
            )


@given(
    st_data=strategy("bytes", min_size=1, max_size=3),
)
def test_executeActions_rev_length_contract(cf, st_data):
    with reverts("Vault: must call contract/function"):
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            [[cf.stakeManager, 0, st_data]],
        )


@given(
    st_dstChain=strategy("uint32"),
    st_dstAddress=strategy("bytes"),
    st_dstToken=strategy("uint16"),
    st_native_transfer=strategy("uint256", min_value=1, max_value=TEST_AMNT),
    st_native_vault=strategy("uint256", max_value=TEST_AMNT),
)
def test_executeActions_rev_nativeBals(
    cf,
    Vault,
    st_dstChain,
    st_dstAddress,
    st_dstToken,
    st_native_transfer,
    st_native_vault,
):

    # For the call to not fail we need a valid message call or a contract
    # with a fallback function, since data cannot be empty.
    # We deploy another Vault as a proxy for a bridge contract.
    externalVault = cf.deployer.deploy(Vault, NON_ZERO_ADDR)

    # Assert initial native balances are zero
    assert web3.eth.get_balance(cf.vault.address) == 0
    assert web3.eth.get_balance(externalVault.address) == 0

    cf.SAFEKEEPER.transfer(cf.vault.address, st_native_vault)

    calldata = externalVault.xSwapNative.encode_input(
        st_dstChain, st_dstAddress, st_dstToken
    )

    if st_native_vault >= st_native_transfer:
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            [[externalVault, st_native_transfer, calldata]],
        )
        assert (
            web3.eth.get_balance(cf.vault.address)
            == st_native_vault - st_native_transfer
        )
        assert web3.eth.get_balance(externalVault.address) == st_native_transfer
    else:
        with reverts("Transaction reverted without a reason string"):
            signed_call_cf(
                cf,
                cf.vault.executeActions,
                [[externalVault, st_native_transfer, calldata]],
            )
        assert web3.eth.get_balance(cf.vault.address) == st_native_vault
        assert web3.eth.get_balance(externalVault.address) == 0


@given(
    st_dstChain=strategy("uint32"),
    st_dstAddress=strategy("bytes"),
    st_dstToken=strategy("uint16"),
    st_native_amount=strategy("uint256", min_value=1, max_value=TEST_AMNT),
)
def test_executeActions_bridge_native(
    cf, Vault, st_dstChain, st_dstAddress, st_dstToken, st_native_amount
):

    # For the call to not fail we need a valid message call or a contract
    # with a fallback function, since data cannot be empty.
    # We deploy another Vault as a proxy for a bridge contract.
    externalVault = cf.deployer.deploy(Vault, NON_ZERO_ADDR)

    # Assert initial native balances are zero
    assert web3.eth.get_balance(cf.vault.address) == 0
    assert web3.eth.get_balance(externalVault.address) == 0

    cf.SAFEKEEPER.transfer(cf.vault.address, st_native_amount)

    calldata = externalVault.xSwapNative.encode_input(
        st_dstChain, st_dstAddress, st_dstToken
    )

    tx = signed_call_cf(
        cf,
        cf.vault.executeActions,
        [[externalVault, st_native_amount, calldata]],
    )
    assert web3.eth.get_balance(cf.vault.address) == 0
    assert web3.eth.get_balance(externalVault.address) == st_native_amount

    assert tx.events["SwapNative"][0].values() == [
        st_dstChain,
        hexStr(st_dstAddress),
        st_dstToken,
        st_native_amount,
        cf.vault.address,
    ]


@given(
    st_dstChain=strategy("uint32"),
    st_dstAddress=strategy("bytes"),
    st_dstToken=strategy("uint16"),
    st_token_approve=strategy("uint256", min_value=1, max_value=TEST_AMNT),
    st_token_swap=strategy("uint256", min_value=1, max_value=TEST_AMNT),
)
def test_executeActions_bridge_token(
    cf,
    Vault,
    st_dstChain,
    st_dstAddress,
    st_dstToken,
    st_token_approve,
    token,
    st_token_swap,
):

    # For the call to not fail we need a valid message call or a contract
    # with a fallback function, since data cannot be empty.
    # We deploy another Vault as a proxy for a bridge contract.
    externalVault = cf.deployer.deploy(Vault, NON_ZERO_ADDR)

    # Assert initial native balances are zero
    assert token.balanceOf(cf.vault.address) == 0
    assert token.balanceOf(externalVault.address) == 0

    token.transfer(cf.vault.address, st_token_approve, {"from": cf.SAFEKEEPER})

    calldata0 = token.approve.encode_input(externalVault, st_token_approve)
    calldata1 = externalVault.xSwapToken.encode_input(
        st_dstChain, st_dstAddress, st_dstToken, token, st_token_swap
    )

    if st_token_approve >= st_token_swap:
        tx = signed_call_cf(
            cf,
            cf.vault.executeActions,
            [[token, 0, calldata0], [externalVault, 0, calldata1]],
        )
        assert token.balanceOf(cf.vault.address) == st_token_approve - st_token_swap
        assert token.balanceOf(externalVault.address) == st_token_swap

        assert tx.events["SwapToken"][0].values() == [
            st_dstChain,
            hexStr(st_dstAddress),
            st_dstToken,
            token,
            st_token_swap,
            cf.vault.address,
        ]
    else:
        with reverts(REV_MSG_ERC20_EXCEED_BAL):
            signed_call_cf(
                cf,
                cf.vault.executeActions,
                [[token, 0, calldata0], [externalVault, 0, calldata1]],
            )
        # Both actions should have reverted
        assert token.balanceOf(cf.vault.address) == st_token_approve
        assert token.balanceOf(externalVault.address) == 0


## TODO: Try interactions with Axelar/CCTP (Goerli?)
