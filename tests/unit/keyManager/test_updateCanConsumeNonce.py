from consts import *
from deploy import deploy_initial_Chainflip_contracts
from shared_tests import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy


@given(
    currentAddrs=strategy("address[]", unique=False),
    newAddrs=strategy("address[]", unique=False),
    st_sender=strategy("address"),
)
def test_updateCanConsumeKeyNonce_rev_length(a, cf, currentAddrs, newAddrs, st_sender):
    assert cf.keyManager.getNumberWhitelistedAddresses() == len(cf.whitelisted)

    if len(currentAddrs) != cf.keyManager.getNumberWhitelistedAddresses():
        with reverts(REV_MSG_LENGTH):
            updateCanConsumeKeyNonce(cf.keyManager, currentAddrs, newAddrs, st_sender)

    # will never match the actual whitelisted addresses since addresses
    # are chosen among a, and the whitelist has newly deployed contracts
    else:
        with reverts(REV_MSG_CANNOT_DEWHITELIST):
            updateCanConsumeKeyNonce(cf.keyManager, currentAddrs, newAddrs, st_sender)


@given(
    newAddrs=strategy("address[]"),
    st_sender=strategy("address"),
)
def test_updateCanConsumeKeyNonce_rev_duplicate(a, cf, newAddrs, st_sender):
    assert cf.keyManager.getNumberWhitelistedAddresses() == len(cf.whitelisted)

    unique = len(set(newAddrs)) == len(newAddrs)

    if unique == False:
        with reverts(REV_MSG_DUPLICATE):
            updateCanConsumeKeyNonce(cf.keyManager, cf.whitelisted, newAddrs, st_sender)

    else:
        newAddrs = newAddrs + [cf.keyManager]
        updateCanConsumeKeyNonce(cf.keyManager, cf.whitelisted, newAddrs, st_sender)

        # Removed previous whitelisted addresses
        for addr in cf.whitelisted:
            if addr not in newAddrs:
                assert cf.keyManager.canConsumeKeyNonce(addr) == False

        # Whitelisted new addresses
        for addr in newAddrs:
            assert cf.keyManager.canConsumeKeyNonce(addr) == True

        assert cf.keyManager.getNumberWhitelistedAddresses() == len(newAddrs)


@given(
    addrsList1=strategy("address[]", unique=True),
    addrsList2=strategy("address[]", unique=True),
    st_sender=strategy("address"),
)
def test_updateCanConsumeKeyNonce_multiple(a, cf, addrsList1, addrsList2, st_sender):
    # Add the keyManager address to the whitelist so it can keep being updated
    if cf.keyManager.address not in addrsList1:
        addrsList1 += [cf.keyManager.address]
    if cf.keyManager.address not in addrsList2:
        addrsList2 += [cf.keyManager.address]

    listAddresses = [addrsList1, addrsList2, addrsList2, addrsList1]
    currentAddrs = cf.whitelisted

    for newAddrs in listAddresses:

        updateCanConsumeKeyNonce(cf.keyManager, currentAddrs, newAddrs, st_sender)

        # Removed previous whitelisted addresses that are not whitelisted again
        for addr in currentAddrs:
            if addr not in newAddrs:
                assert cf.keyManager.canConsumeKeyNonce(addr) == False

        # Whitelisted new addresses
        for addr in newAddrs:
            assert cf.keyManager.canConsumeKeyNonce(addr) == True

        assert cf.keyManager.getNumberWhitelistedAddresses() == len(newAddrs)
        currentAddrs = newAddrs


def test_updateCanConsumeKeyNonce_rev_noKeyManager(a, cf):

    # Using [:] to create a copy of the list (instead of reference)
    listAddresses = cf.whitelisted[:]
    listAddresses.remove(cf.keyManager)

    with reverts(REV_MSG_KEYMANAGER_WHITELIST):
        updateCanConsumeKeyNonce(cf.keyManager, cf.whitelisted, listAddresses, a[0])
