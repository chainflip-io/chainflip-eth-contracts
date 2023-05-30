from consts import *
from brownie import reverts
from brownie.test import given, strategy
from utils import *
from shared_tests import *


@given(
    st_sender=strategy("address"),
    st_fetchSwapID=strategy("bytes32"),
    st_deployToken=strategy("bool"),
)
def test_deposit(cf, token, st_sender, st_fetchSwapID, st_deployToken):
    tx = signed_call_cf(
        cf,
        cf.vault.deployAndFetchBatch,
        [[st_fetchSwapID, token.address if st_deployToken else NATIVE_ADDR]],
        sender=st_sender,
    )

    if not st_deployToken:
        assert len(tx.events["FetchedNative"]) == 1
        assert tx.events["FetchedNative"][0].values() == [0]


@given(
    st_sender=strategy("address"),
    st_address=strategy("address", exclude=NATIVE_ADDR),
    st_fetchSwapID=strategy("bytes32"),
    st_deployToken=strategy("bool"),
)
def test_deposit_constructor(
    cf, st_sender, st_address, st_fetchSwapID, token, st_deployToken
):
    # Non existing token in that address
    with reverts():
        signed_call_cf(cf, cf.vault.deployAndFetchBatch, [[st_fetchSwapID, st_address]])

    tx = signed_call_cf(
        cf,
        cf.vault.deployAndFetchBatch,
        [[st_fetchSwapID, token.address if st_deployToken else NATIVE_ADDR]],
        sender=st_sender,
    )
    if not st_deployToken:
        assert len(tx.events["FetchedNative"]) == 1
        assert tx.events["FetchedNative"][0].values() == [0]


@given(
    st_sender=strategy("address"),
    st_sender_2=strategy("address"),
    st_fetchSwapID=strategy("bytes32"),
    st_deployToken=strategy("bool"),
    st_fetchToken=strategy("bool"),
)
def test_deposit_fetch(
    cf,
    token,
    st_sender,
    st_fetchSwapID,
    st_deployToken,
    Deposit,
    st_sender_2,
    st_fetchToken,
):
    depositAddr = getCreate2Addr(
        cf.vault.address,
        st_fetchSwapID.hex(),
        Deposit,
        cleanHexStrPad(token.address)
        if st_deployToken
        else cleanHexStrPad(NATIVE_ADDR),
    )
    tx = signed_call_cf(
        cf,
        cf.vault.deployAndFetchBatch,
        [[st_fetchSwapID, token.address if st_deployToken else NATIVE_ADDR]],
        sender=st_sender,
    )
    if not st_deployToken:
        assert len(tx.events["FetchedNative"]) == 1
        assert tx.events["FetchedNative"][0].values() == [0]

    # Call fetch function on the deployed Deposit contract - should fail as only the Vault should be able to call it
    with reverts():
        Deposit.at(depositAddr).fetch(
            token.address if st_fetchToken else NATIVE_ADDR, {"from": st_sender_2}
        )

    tx = signed_call_cf(
        cf,
        cf.vault.fetchBatch,
        [[depositAddr, NATIVE_ADDR], [depositAddr, token.address]],
        sender=st_sender,
    )
    if not st_deployToken:
        assert len(tx.events["FetchedNative"]) == 1
        assert tx.events["FetchedNative"][0].values() == [0]
