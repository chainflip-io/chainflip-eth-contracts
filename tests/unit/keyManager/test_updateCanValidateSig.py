from consts import *
from deploy import deploy_initial_Chainflip_contracts
from shared_tests import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy


@given(
    currentAddrs=strategy("address[]", unique=False),
    newAddrs=strategy("address[]", unique=False),
)
def test_updateCanValidateSig_rev_length(a, cf, currentAddrs, newAddrs):
    assert cf.keyManager.getNumberWhitelistedAddresses() == len(cf.whitelisted)

    callDataNoSig = cf.keyManager.updateCanValidateSig.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), currentAddrs, newAddrs
    )

    if len(currentAddrs) != cf.keyManager.getNumberWhitelistedAddresses():
        with reverts(REV_MSG_LENGTH):
            cf.keyManager.updateCanValidateSig(
                AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
                currentAddrs,
                newAddrs,
            )
    # will never match the actual whitelisted addresses since addresses
    # are chosen among a, and the whitelist has newly deployed contracts
    else:
        with reverts(REV_MSG_NOT_DEWHITELISTED):
            cf.keyManager.updateCanValidateSig(
                AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
                currentAddrs,
                newAddrs,
            )


@given(
    newAddrs=strategy("address[]"),
)
def test_updateCanValidateSig_rev_duplicate(a, cf, newAddrs):
    assert cf.keyManager.getNumberWhitelistedAddresses() == len(cf.whitelisted)

    callDataNoSig = cf.keyManager.updateCanValidateSig.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), cf.whitelisted, newAddrs
    )
    unique = len(set(newAddrs)) == len(newAddrs)

    if unique == False:
        with reverts(REV_MSG_DUPLICATE):
            cf.keyManager.updateCanValidateSig(
                AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
                cf.whitelisted,
                newAddrs,
            )
    else:
        tx = cf.keyManager.updateCanValidateSig(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            cf.whitelisted,
            newAddrs,
        )
        # Removed previous whitelisted addresses
        for addr in cf.whitelisted:
            assert cf.keyManager.canValidateSig(addr) == False

        # Whitelisted new addresses
        for addr in newAddrs:
            assert cf.keyManager.canValidateSig(addr) == True

        assert cf.keyManager.getNumberWhitelistedAddresses() == len(newAddrs)


@given(
    addrsList1=strategy("address[]", unique=True),
    addrsList2=strategy("address[]", unique=True),
)
def test_updateCanValidateSig_multiple(a, cf, addrsList1, addrsList2):
    # Add the keyManager address to the whitelist so it can keep being updated
    if cf.keyManager.address not in addrsList1:
        addrsList1 += [cf.keyManager.address]
    if cf.keyManager.address not in addrsList2:
        addrsList2 += [cf.keyManager.address]

    listAddresses = [addrsList1, addrsList2, addrsList2, addrsList1]
    currentAddrs = cf.whitelisted

    for newAddrs in listAddresses:

        callDataNoSig = cf.keyManager.updateCanValidateSig.encode_input(
            agg_null_sig(cf.keyManager.address, chain.id), currentAddrs, newAddrs
        )

        cf.keyManager.updateCanValidateSig(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            currentAddrs,
            newAddrs,
        )

        # Removed previous whitelisted addresses that are not whitelisted again
        for addr in currentAddrs:
            if addr not in newAddrs:
                assert cf.keyManager.canValidateSig(addr) == False

        # Whitelisted new addresses
        for addr in newAddrs:
            assert cf.keyManager.canValidateSig(addr) == True

        assert cf.keyManager.getNumberWhitelistedAddresses() == len(newAddrs)
        currentAddrs = newAddrs


def test_updateCanValidateSig_noKeyManager(a, cf):

    # Using [:] to create a copy of the list (instead of reference)
    listAddresses = cf.whitelisted[:]
    listAddresses.remove(cf.keyManager)
    print(cf.whitelisted)
    print(listAddresses)

    callDataNoSig = cf.keyManager.updateCanValidateSig.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), cf.whitelisted, listAddresses
    )
    cf.keyManager.updateCanValidateSig(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        cf.whitelisted,
        listAddresses,
    )

    callDataNoSig = cf.keyManager.updateCanValidateSig.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), listAddresses, list(a)
    )

    # updateCanValidateSig has been bricked since KeyManager itself is not whitelisted
    with reverts(REV_MSG_WHITELIST):
        cf.keyManager.updateCanValidateSig(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            listAddresses,
            list(a),
        )
