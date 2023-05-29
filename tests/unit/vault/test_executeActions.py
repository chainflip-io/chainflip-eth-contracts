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
            [cf.flip, st_multicall, 2**256 - 1],
            [[0, ZERO_ADDR, 0, JUNK_HEX, JUNK_HEX]],
            100000,
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
        [cf.flip, multicall, 2**256 - 1],
        [[0, ZERO_ADDR, 0, JUNK_HEX, JUNK_HEX]],
        100000,
        sender=st_sender,
    )

    # It should revert when doing the safeTransferFrom. Not asserting
    # the revert message as it's not important for now.
    assert tx.events["ExecuteActionsFailed"][0].values()[:-1] == [
        multicall,
        2**256 - 1,
        cf.flip.address,
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
    args = [[cf.flip, multicall, st_amount], [call], 100000]

    tx = signed_call_cf(
        cf,
        cf.vault.executeActions,
        *args,
        sender=st_sender,
    )

    if st_amount > st_ini_amount:
        assert tx.events["ExecuteActionsFailed"][0].values()[:-1] == [
            multicall,
            st_amount,
            cf.flip.address,
        ]
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
    args = [[ZERO_ADDR, multicall, 0], [call], 100000]

    tx = signed_call_cf(
        cf,
        cf.vault.executeActions,
        *args,
        sender=st_sender,
    )
    assert tx.events["ExecuteActionsFailed"][0].values()[:-1] == [
        multicall,
        0,
        ZERO_ADDR,
    ]

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
    args = [[ZERO_ADDR, multicall, 0], [call], 100000]

    tx = signed_call_cf(
        cf,
        cf.vault.executeActions,
        *args,
        sender=st_sender,
    )
    assert tx.events["ExecuteActionsFailed"][0].values()[:-1] == [
        multicall,
        0,
        ZERO_ADDR,
    ]


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
    args = [[ZERO_ADDR, st_receiver, 0], [call], st_gas]

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

    args = [[NATIVE_ADDR, multicall, st_native_transfer], [call], 100000]

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
        assert tx.events["ExecuteActionsFailed"][0].values()[:-1] == [
            multicall,
            st_native_transfer,
            NATIVE_ADDR,
        ]

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

    args = [[token, multicall, st_token_transfer], [call], 1000000]

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
        assert tx.events["ExecuteActionsFailed"][0].values()[:-1] == [
            multicall,
            st_token_transfer,
            token.address,
        ]
        assert token.balanceOf(multicall.address) == ini_bals_multicall
        assert token.balanceOf(cf.vault.address) == ini_bals_vault
        assert token.balanceOf(cf.ALICE.address) == ini_bals_alice

        assert token.allowance(cf.vault.address, multicall.address) == 0


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

    args = [[cf.flip.address, multicall, st_amount], [call], 1000000]

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

    args = [[NATIVE_ADDR, multicall, st_amount], [call], 1000000]

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
    # Number used just for a unit test, approximatted via gas test.
    multicall_gas = 70000
    args = [[cf.flip.address, multicall, TEST_AMNT], [call], multicall_gas]

    sigData = AGG_SIGNER_1.getSigDataWithNonces(
        cf.keyManager, cf.vault.executeActions, nonces, *args
    )
    # Gas limit that doesn't allow the Multicall to execute the actions
    # but leaves enough gas to trigger "Vault: gasMulticall too low".
    # Succesfull tx according to gas test is ~140k but it doesn't succeed
    # until gas_limit is not at least 180k. Then from 180k to 190, when adding
    # the gas check, it reverts with "Vault: gasMulticall too low". After 190k
    # it will succeed as normal
    gas_limit = 180000

    # Reverted with empty revert string is to catch the invalid opcode
    # That is different to the "Transaction reverted without a reason string"
    with reverts(REV_MSG_INSUFFICIENT_GAS):
        cf.vault.executeActions(
            sigData,
            *args,
            {"from": cf.DENICE, "gas_limit": gas_limit},
        )

    gas_limit = 190000

    tx = cf.vault.executeActions(
        sigData,
        *args,
        {"from": cf.DENICE, "gas_limit": gas_limit},
    )
    assert "ExecuteActionsFailed" not in tx.events


@given(
    st_gas_limit=strategy("uint256", min_value=80000, max_value=250000),
)
def test_executeActions_gas(cf, multicall, st_gas_limit):
    print("gas limit", st_gas_limit)
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
    # Number used just for a unit test, approximatted via gas test.
    multicall_gas = 70000
    args = [[cf.flip.address, multicall, TEST_AMNT], [call], multicall_gas]

    sigData = AGG_SIGNER_1.getSigDataWithNonces(
        cf.keyManager, cf.vault.executeActions, nonces, *args
    )

    # Exact gas limit that makes the transaction have enough gas to pass the
    # gas check, execute the actions and succeeed.
    # cutoff_gas_limit = 181965
    cutoff_gas_limit = 192129

    # On low gas_limit values it will revert with not enough gas error and other
    # error such as no reason string. Arbitrary 80k under the cutoff gas limit
    # for those kinds of errors.
    if st_gas_limit < cutoff_gas_limit - 80000:
        with reverts():
            cf.vault.executeActions(
                sigData,
                *args,
                {"from": cf.DENICE, "gas_limit": st_gas_limit},
            )
    elif st_gas_limit < cutoff_gas_limit:
        # Reverted with empty revert string is to catch the invalid opcode
        # That is different to the "Transaction reverted without a reason string"
        with reverts(REV_MSG_INSUFFICIENT_GAS):
            cf.vault.executeActions(
                sigData,
                *args,
                {"from": cf.DENICE, "gas_limit": st_gas_limit},
            )
    # If the gas check passes, it should always succeed.
    else:
        tx = cf.vault.executeActions(
            sigData,
            *args,
            {"from": cf.DENICE, "gas_limit": st_gas_limit},
        )
        assert "ExecuteActionsFailed" not in tx.events


# TODO: Try same test as before but with a failing execute actions to assert that if
# the gas check passes, an "ExecuteActionsFailed" will be emitted.
