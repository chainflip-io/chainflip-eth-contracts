from consts import *
from brownie import reverts


def test_constructor(cf):
    constructor_test(cf, cf.stateChainGateway)
    constructor_test(cf, cf.vault)


def test_communityGuard(cf):
    communityGuard_test(cf, cf.stateChainGateway)
    communityGuard_test(cf, cf.vault)


def constructor_test(cf, governanceCommunityGuarded):
    assert governanceCommunityGuarded.getCommunityKey() == cf.COMMUNITY_KEY
    assert governanceCommunityGuarded.getCommunityGuardDisabled() == False
    assert governanceCommunityGuarded.getSuspendedState() == False


def communityGuard_test(cf, governanceCommunityGuarded):
    with reverts(REV_MSG_GOV_NOT_COMMUNITY):
        governanceCommunityGuarded.disableCommunityGuard({"from": cf.ALICE})
    # Setting Guard to the same value to ensure that nothing weird happens
    with reverts(REV_MSG_GOV_ENABLED_GUARD):
        tx = governanceCommunityGuarded.enableCommunityGuard({"from": cf.COMMUNITY_KEY})
    assert governanceCommunityGuarded.getCommunityGuardDisabled() == False
    assert governanceCommunityGuarded.getCommunityKey() == cf.COMMUNITY_KEY
    # Disable Guard
    tx = governanceCommunityGuarded.disableCommunityGuard({"from": cf.COMMUNITY_KEY})
    assert tx.events["CommunityGuardDisabled"][0].values()[0] == True
    assert governanceCommunityGuarded.getCommunityGuardDisabled() == True
    assert governanceCommunityGuarded.getCommunityKey() == cf.COMMUNITY_KEY
    with reverts(REV_MSG_GOV_DISABLED_GUARD):
        governanceCommunityGuarded.disableCommunityGuard({"from": cf.COMMUNITY_KEY})

    # Enable again
    with reverts(REV_MSG_GOV_NOT_COMMUNITY):
        governanceCommunityGuarded.enableCommunityGuard({"from": cf.ALICE})
    tx = governanceCommunityGuarded.enableCommunityGuard({"from": cf.COMMUNITY_KEY})
    assert tx.events["CommunityGuardDisabled"][0].values()[0] == False
    assert governanceCommunityGuarded.getCommunityGuardDisabled() == False
    assert governanceCommunityGuarded.getCommunityKey() == cf.COMMUNITY_KEY
