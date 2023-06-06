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

    # Should fail if we pass a NATIVE_ADDR as the token address
    with reverts():
        signed_call_cf(
            cf,
            cf.vault.fetchBatch,
            [[depositAddr, NATIVE_ADDR], [depositAddr, token.address]],
            sender=st_sender,
        )

    tx = signed_call_cf(
        cf,
        cf.vault.fetchBatch,
        [[depositAddr, token.address]],
        sender=st_sender,
    )
    assert "FetchedNative" not in tx.events


def deploy_deposit(cf, sender, Deposit):
    depositAddr = getCreate2Addr(
        cf.vault.address,
        JUNK_HEX_PAD,
        Deposit,
        cleanHexStrPad(NATIVE_ADDR),
    )

    tx = signed_call_cf(
        cf,
        cf.vault.deployAndFetchBatch,
        [[JUNK_HEX_PAD, NATIVE_ADDR]],
        sender=sender,
    )

    assert tx.events["FetchedNative"][0].values() == [0]

    return depositAddr


# Note that a transfer of zero does work and triggers the receive function
@given(
    st_sender=strategy("address"),
    st_amount=strategy("uint256", max_value=TEST_AMNT * 10),
)
def test_receive(cf, st_sender, token, Deposit, st_amount):
    depositAddr = deploy_deposit(cf, st_sender, Deposit)

    # Tokens do not trigger any receive function
    tx = token.transfer(depositAddr, st_amount, {"from": cf.SAFEKEEPER})
    assert "FetchedNative" not in tx.events

    iniVault_nativeBals = web3.eth.get_balance(cf.vault.address)
    # Send some ETH to the deposit contract
    tx = st_sender.transfer(depositAddr, st_amount)
    assert tx.events["FetchedNative"][0].values() == [st_amount]
    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
    assert web3.eth.get_balance(cf.vault.address) == iniVault_nativeBals + st_amount


@given(
    st_gasLimit=strategy("uint256", min_value=22000, max_value=40000),
    st_amount=strategy("uint256", min_value=1),
)
def test_receive_gas(cf, Deposit, st_gasLimit, st_amount):
    depositAddr = deploy_deposit(cf, cf.ALICE, Deposit)

    # As of now a transfer of >0 ETH will require ~31.602 gas which ends up being 33776 gas
    # required as a gas Limit (most likely due to the 64/63 rule).
    if st_gasLimit < 33776:
        # Brownie is unable to catch this with `reverts()`. It caches it in a normal
        # call using {"gas_limit": st_gas_limit} but not here - using a workaround.
        try:
            tx = cf.DENICE.transfer(depositAddr, st_amount, gas_limit=st_gasLimit)
        except Exception:
            pass
        else:
            tx.info()
            assert False, "Call should be reverting due to not enough gas"
    else:
        tx = cf.DENICE.transfer(depositAddr, st_amount, gas_limit=st_gasLimit)
        assert tx.events["FetchedNative"][0].values() == [st_amount]
        tx.info()
