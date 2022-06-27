from consts import *
from deploy import deploy_initial_Chainflip_contracts
from shared_tests import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy


@given(
    st_currentAddrs=strategy("address[]", unique=False),
    st_newAddrs=strategy("address[]", unique=False),
    st_sender=strategy("address"),
)
def test_updateCanConsumeKeyNonce_rev_length(
    a, cf, st_currentAddrs, st_newAddrs, st_sender
):
    assert cf.keyManager.getNumberWhitelistedAddresses() == len(cf.whitelisted)

    if len(st_currentAddrs) != cf.keyManager.getNumberWhitelistedAddresses():
        with reverts(REV_MSG_LENGTH):
            signed_call_cf(
                cf,
                cf.keyManager.updateCanConsumeKeyNonce,
                st_currentAddrs,
                st_newAddrs,
                sender=st_sender,
            )

    # will never match the actual whitelisted addresses since addresses
    # are chosen among a, and the whitelist has newly deployed contracts
    else:
        with reverts(REV_MSG_CANNOT_DEWHITELIST):
            signed_call_cf(
                cf,
                cf.keyManager.updateCanConsumeKeyNonce,
                st_currentAddrs,
                st_newAddrs,
                sender=st_sender,
            )


@given(
    st_newAddrs=strategy("address[]"),
    st_sender=strategy("address"),
)
def test_updateCanConsumeKeyNonce_rev_duplicate(a, cf, st_newAddrs, st_sender):
    assert cf.keyManager.getNumberWhitelistedAddresses() == len(cf.whitelisted)

    unique = len(set(st_newAddrs)) == len(st_newAddrs)

    if unique == False:
        with reverts(REV_MSG_DUPLICATE):
            signed_call_cf(
                cf,
                cf.keyManager.updateCanConsumeKeyNonce,
                cf.whitelisted,
                st_newAddrs,
                sender=st_sender,
            )

    else:
        st_newAddrs = st_newAddrs + [cf.keyManager]
        tx = signed_call_cf(
            cf,
            cf.keyManager.updateCanConsumeKeyNonce,
            cf.whitelisted,
            st_newAddrs,
            sender=st_sender,
        )
        assert tx.events["KeyNonceConsumersUpdated"][0].values() == (
            cf.whitelisted,
            st_newAddrs,
        )

        # Removed previous whitelisted addresses
        for addr in cf.whitelisted:
            if addr not in st_newAddrs:
                assert cf.keyManager.canConsumeKeyNonce(addr) == False

        # Whitelisted new addresses
        for addr in st_newAddrs:
            assert cf.keyManager.canConsumeKeyNonce(addr) == True

        assert cf.keyManager.getNumberWhitelistedAddresses() == len(st_newAddrs)


@given(
    st_addrsList1=strategy("address[]", unique=True),
    st_addrsList2=strategy("address[]", unique=True),
    st_sender=strategy("address"),
)
def test_updateCanConsumeKeyNonce_multiple(
    a, cf, st_addrsList1, st_addrsList2, st_sender
):
    # Add the keyManager address to the whitelist so it can keep being updated
    if cf.keyManager.address not in st_addrsList1:
        st_addrsList1 += [cf.keyManager.address]
    if cf.keyManager.address not in st_addrsList2:
        st_addrsList2 += [cf.keyManager.address]

    listAddresses = [st_addrsList1, st_addrsList2, st_addrsList2, st_addrsList1]
    st_currentAddrs = cf.whitelisted

    for st_newAddrs in listAddresses:
        tx = signed_call_cf(
            cf,
            cf.keyManager.updateCanConsumeKeyNonce,
            st_currentAddrs,
            st_newAddrs,
            sender=st_sender,
        )

        assert tx.events["KeyNonceConsumersUpdated"][0].values() == (
            st_currentAddrs,
            st_newAddrs,
        )

        # Removed previous whitelisted addresses that are not whitelisted again
        for addr in st_currentAddrs:
            if addr not in st_newAddrs:
                assert cf.keyManager.canConsumeKeyNonce(addr) == False

        # Whitelisted new addresses
        for addr in st_newAddrs:
            assert cf.keyManager.canConsumeKeyNonce(addr) == True

        assert cf.keyManager.getNumberWhitelistedAddresses() == len(st_newAddrs)
        st_currentAddrs = st_newAddrs


def test_updateCanConsumeKeyNonce_rev_noKeyManager(a, cf):

    # Using [:] to create a copy of the list (instead of reference)
    st_newAddrs = cf.whitelisted[:]
    st_newAddrs.remove(cf.keyManager)

    with reverts(REV_MSG_KEYMANAGER_WHITELIST):
        signed_call_cf(
            cf, cf.keyManager.updateCanConsumeKeyNonce, cf.whitelisted, st_newAddrs
        )
