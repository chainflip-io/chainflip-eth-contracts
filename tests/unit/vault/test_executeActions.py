from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy
from brownie.convert import to_bytes


@given(
    st_sender=strategy("address"),
    st_multicall=strategy("address"),
)
def test_executeActions_rev_eoa(cf, st_sender, st_multicall):

    # This won't revert with REV_MSG_ERC20_EXCEED_BAL as we are approving
    # now instead of transferring. It will fail the eoa check.
    with reverts("Transaction reverted without a reason string"):
        signed_call_cf(
            cf,
            cf.vault.executeActions,
            cf.flip,
            2**256 - 1,
            st_multicall,
            100000,
            [[0, ZERO_ADDR, 0, JUNK_HEX, JUNK_HEX]],
            sender=st_sender,
        )


@given(
    st_sender=strategy("address"),
)
def test_executeActions_rev_erc20_max(cf, st_sender, multicall):

    cf.flip.transfer(cf.vault, TEST_AMNT, {"from": cf.SAFEKEEPER})

    assert cf.flip.balanceOf(cf.vault) == TEST_AMNT

    tx = signed_call_cf(
        cf,
        cf.vault.executeActions,
        cf.flip,
        2**256 - 1,
        multicall,
        100000,
        [[0, ZERO_ADDR, 0, JUNK_HEX, JUNK_HEX]],
        sender=st_sender,
    )

    # It should revert when doing the safeTransferFrom
    assert tx.events["ExecuteActionsFailed"][0].values() == [
        cf.flip,
        2**256 - 1,
        multicall,
    ]
    assert cf.flip.allowance(cf.vault, multicall) == 0

    assert cf.flip.balanceOf(cf.vault) == TEST_AMNT


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
    args = [cf.flip, st_amount, multicall, 100000, [call]]

    tx = signed_call_cf(
        cf,
        cf.vault.executeActions,
        *args,
        sender=st_sender,
    )

    if st_amount > st_ini_amount:
        assert "ExecuteActionsFailed" in tx.events
    else:
        assert "ExecuteActionsFailed" not in tx.events

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
    args = [ZERO_ADDR, 0, multicall, 100000, [call]]

    tx = signed_call_cf(
        cf,
        cf.vault.executeActions,
        *args,
        sender=st_sender,
    )
    assert "ExecuteActionsFailed" in tx.events

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
    args = [ZERO_ADDR, 0, multicall, 100000, [call]]

    tx = signed_call_cf(
        cf,
        cf.vault.executeActions,
        *args,
        sender=st_sender,
    )
    assert "ExecuteActionsFailed" in tx.events


@given(
    st_data=strategy("bytes"),
    st_receiver=strategy("address"),
    st_amount=strategy("uint256"),
    st_enum=strategy("uint256", max_value=3),
    st_sender=strategy("address"),
    st_gas=strategy("uint256"),
)
def test_executeActions_rev_length_eoa(
    cf, st_data, st_receiver, st_amount, st_enum, st_sender, st_gas
):

    ## Ensure we can't call a cfReceive or cfReceivexCall function via Multicall
    call = [
        st_enum,
        st_receiver,
        st_amount,
        st_data,
        st_data,
    ]
    args = [ZERO_ADDR, 0, st_receiver, st_gas, [call]]

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

    args = [NATIVE_ADDR, st_native_transfer, multicall, 100000, [call]]

    tx = signed_call_cf(
        cf,
        cf.vault.executeActions,
        *args,
        sender=st_sender,
    )
    if st_native_vault >= st_native_transfer:
        assert "ExecuteActionsFailed" not in tx.events
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
        assert "ExecuteActionsFailed" in tx.events

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

    args = [token, st_token_transfer, multicall, 1000000, [call]]

    tx = signed_call_cf(
        cf,
        cf.vault.executeActions,
        *args,
        sender=st_sender,
    )

    if st_token_vault >= st_token_transfer:
        assert "ExecuteActionsFailed" not in tx.events

        assert token.balanceOf(cf.vault.address) == ini_bals_vault - st_token_transfer
        assert token.balanceOf(multicall.address) == 0
        assert token.balanceOf(cf.ALICE.address) == ini_bals_alice + st_token_transfer
    else:
        assert "ExecuteActionsFailed" in tx.events

        assert token.balanceOf(multicall.address) == ini_bals_multicall
        assert token.balanceOf(cf.vault.address) == ini_bals_vault
        assert token.balanceOf(cf.ALICE.address) == ini_bals_alice


@given(
    st_amount=strategy("uint256", min_value=1, max_value=TEST_AMNT),
)
def test_multicallRun_safeTransferFrom(cf, multicall, st_amount):

    cf.flip.transfer(cf.vault.address, st_amount, {"from": cf.SAFEKEEPER})

    # Dummy call because brownie struggles to encode an empty array
    call = [
        0,
        cf.flip,
        0,
        cf.flip.transfer.encode_input(cf.ALICE, 0),
        0,
    ]

    args = [cf.flip.address, st_amount, multicall, 1000000, [call]]

    assert cf.flip.balanceOf(multicall) == 0

    signed_call_cf(
        cf,
        cf.vault.executeActions,
        *args,
    )

    assert cf.flip.balanceOf(multicall) == st_amount


@given(
    st_amount=strategy("uint256", min_value=1, max_value=TEST_AMNT),
)
def test_multicallRun_native(cf, multicall, st_amount):
    cf.SAFEKEEPER.transfer(cf.vault.address, st_amount)

    # Dummy call because brownie struggles to encode an empty array
    call = [
        0,
        cf.flip,
        0,
        cf.flip.transfer.encode_input(cf.ALICE, 0),
        0,
    ]

    args = [NATIVE_ADDR, st_amount, multicall, 1000000, [call]]

    assert web3.eth.get_balance(multicall.address) == 0

    signed_call_cf(
        cf,
        cf.vault.executeActions,
        *args,
    )
    assert web3.eth.get_balance(multicall.address) == st_amount


@given(
    st_sender=strategy("address"),
)
def test_multicallRun_rev_notVault(
    st_sender,
    multicall,
):
    with reverts("Multicall: not Chainflip Vault"):
        multicall.run([], st_sender, JUNK_INT, {"from": st_sender})

    with reverts("Multicall: not Chainflip Vault"):
        multicall.run(
            [[0, ZERO_ADDR, JUNK_INT, JUNK_HEX, JUNK_HEX]],
            st_sender,
            JUNK_INT,
            {"from": st_sender},
        )


# Basic unit test for "Vault: gasMulticall too low"
def test_executeActions_revgas(cf, multicall):

    cf.flip.transfer(cf.vault.address, TEST_AMNT, {"from": cf.SAFEKEEPER})

    # Dummy call because brownie struggles to encode an empty array
    call = [
        0,
        cf.flip,
        0,
        cf.flip.transfer.encode_input(cf.ALICE, 1),
        0,
    ]
    # Gas that should be sent to the Multicall for safeTransferFrom + transfer
    # Number used just for a unit test
    multicall_gas = 70000
    args = [cf.flip.address, TEST_AMNT, multicall, multicall_gas, [call]]

    sigData = AGG_SIGNER_1.getSigDataWithNonces(
        cf.keyManager, cf.vault.executeActions, nonces, *args
    )
    # Gas limit that doesn't allow the Multicall to execute the actions
    # but leaves enough gas to trigger "Vault: gasMulticall too low".
    # Succesfull tx is ~138k
    gas_limit = 130000
    with reverts("Vault: gasMulticall too low"):
        cf.vault.executeActions(
            sigData,
            *args,
            {"from": cf.DENICE, "gas_limit": gas_limit},
        )


# TODO: Add tests for insufficient gas griefing attack. We most likely need to do
# that with fuzzing as python hypothesis struggles - we get a lot of flaky errors.

# @given(
#     st_gas=strategy("uint256", min_value=0, max_value=2000000),
# )
# def test_executeActions_revgas(cf, multicall, token, st_gas):

#     st_token_amount = TEST_AMNT
#     st_sender = cf.BOB
#     st_bytes = JUNK_HEX

#     # Assert initial token balances are zero
#     assert token.balanceOf(cf.vault.address) == 0
#     assert token.balanceOf(multicall.address) == 0

#     token.transfer(cf.vault.address, st_token_amount)

#     ini_bals_multicall = 0
#     ini_bals_vault = token.balanceOf(cf.vault.address)
#     ini_bals_alice = token.balanceOf(cf.ALICE.address)

#     call = [
#         0,
#         token,
#         0,
#         token.transfer.encode_input(cf.ALICE, st_token_amount),
#         st_bytes,
#     ]

#     # Working scenario - executeActions avg (confirmed):  1249009
#     # Working scenario - Mulitcall.Run avg (confirmed):  860480 (might include 21k minimum)
#     print("gas limit: ", st_gas)
#     multicall_gas_needed = 1000000  # Rounded up

#     # Make the multicall spend a lot of gas so 1/64th can still run some logic
#     calls = []
#     for i in range(100):
#         calls.append(
#             [
#                 0,
#                 token,
#                 0,
#                 token.transfer.encode_input(cf.ALICE, i),
#                 JUNK_HEX,
#             ]
#         )

#     args = [token, st_token_amount, multicall, multicall_gas_needed, calls]

#     sigData = AGG_SIGNER_1.getSigDataWithNonces(
#         cf.keyManager, cf.vault.executeActions, nonces, *args
#     )

#     # tx = cf.vault.executeActions(
#     #     sigData,
#     #     *args,
#     #     {"from": cf.DENICE, "gas_limit": st_gas},
#     #     # {"from": cf.DENICE},
#     # )

#     # print("tx.events: ", tx.events)
#     # assert "ExecuteActionsFailed" not in tx.events

#     try:
#         tx = cf.vault.executeActions(
#             sigData,
#             *args,
#             {"from": cf.DENICE, "gas_limit": st_gas},
#             # {"from": cf.DENICE},
#         )

#     except Exception as e:
#         revert_reason = str(e).split("\n", 1)[0]
#         print(f"An error occurred: {e}")
#         # Manually check for all potential revert reasons due to out of gas
#         assert (
#             "revert: Vault: gasMulticall too low" in revert_reason
#             or "Transaction requires at least" in revert_reason
#             or "call to precompile 1 failed" in revert_reason
#             or "Transaction ran out of gas" in revert_reason
#             or "Transaction reverted without a reason string" in revert_reason
#         )
#         tx = None

#     if tx != None:
#         print(tx.events)
#         print(tx.info())
#         assert "ExecuteActionsFailed" not in tx.events
