from consts import *
from brownie import reverts


def test_constructor(cf):
    governanceCommunityGuardedList = getgovernanceCommunityGuardedList(cf)
    for governanceCommunityGuarded in governanceCommunityGuardedList:
        assert governanceCommunityGuarded.getCommunityKey() == cf.COMMUNITY_KEY
        assert governanceCommunityGuarded.getCommunityGuard() == False
        assert governanceCommunityGuarded.getSuspendedState() == False


def test_CommunityGuard(cf):
    governanceCommunityGuardedList = getgovernanceCommunityGuardedList(cf)
    for governanceCommunityGuarded in governanceCommunityGuardedList:
        with reverts(REV_MSG_GOV_NOT_COMMUNITY):
            governanceCommunityGuarded.disableCommunityGuard({"from": cf.ALICE})
        # Setting Guard to the same value to ensure that nothing weird happens
        with reverts(REV_MSG_GOV_ENABLED_GUARD):
            governanceCommunityGuarded.enableCommunityGuard({"from": cf.COMMUNITY_KEY})
        assert governanceCommunityGuarded.getCommunityGuard() == False
        assert governanceCommunityGuarded.getCommunityKey() == cf.COMMUNITY_KEY
        # Disable Guard
        governanceCommunityGuarded.disableCommunityGuard({"from": cf.COMMUNITY_KEY})
        assert governanceCommunityGuarded.getCommunityGuard() == True
        assert governanceCommunityGuarded.getCommunityKey() == cf.COMMUNITY_KEY
        with reverts(REV_MSG_GOV_DISABLED_GUARD):
            governanceCommunityGuarded.disableCommunityGuard({"from": cf.COMMUNITY_KEY})

        # Enable again
        governanceCommunityGuarded.enableCommunityGuard({"from": cf.COMMUNITY_KEY})
        assert governanceCommunityGuarded.getCommunityGuard() == False
        assert governanceCommunityGuarded.getCommunityKey() == cf.COMMUNITY_KEY


def getgovernanceCommunityGuardedList(cf):
    return [cf.stakeManager, cf.vault]
