from consts import *
from brownie import reverts


def test_constructor(cf):
    governanceCommunityGuardedList = getgovernanceCommunityGuardedList(cf)
    for governanceCommunityGuarded in governanceCommunityGuardedList:
        assert governanceCommunityGuarded.getCommunityKey() == cf.COMMUNITY_KEY
        assert governanceCommunityGuarded.getCommunityGuard() == ENABLE_COMMUNITY_GUARD
        assert governanceCommunityGuarded.getSuspendedState() == False


def test_constructor_deploy(cf, Vault, StakeManager):
    with reverts(REV_MSG_NZ_ADDR):
        cf.vault = cf.DEPLOYER.deploy(Vault, cf.keyManager, ZERO_ADDR)

    with reverts(REV_MSG_NZ_ADDR):
        cf.stakeManager = cf.DEPLOYER.deploy(
            StakeManager, cf.keyManager, MIN_STAKE, ZERO_ADDR
        )


def test_setCommunityGuard(cf):
    governanceCommunityGuardedList = getgovernanceCommunityGuardedList(cf)
    for governanceCommunityGuarded in governanceCommunityGuardedList:
        with reverts(REV_MSG_GOV_NOT_COMMUNITY):
            governanceCommunityGuarded.setCommunityGuard(
                DISABLE_COMMUNITY_GUARD, {"from": cf.ALICE}
            )
        # Setting Guard to the same value to ensure that nothing weird happens
        governanceCommunityGuarded.setCommunityGuard(
            ENABLE_COMMUNITY_GUARD, {"from": cf.COMMUNITY_KEY}
        )
        assert governanceCommunityGuarded.getCommunityGuard() == ENABLE_COMMUNITY_GUARD
        assert governanceCommunityGuarded.getCommunityKey() == cf.COMMUNITY_KEY
        # Disable Guard
        governanceCommunityGuarded.setCommunityGuard(
            DISABLE_COMMUNITY_GUARD, {"from": cf.COMMUNITY_KEY}
        )
        assert governanceCommunityGuarded.getCommunityGuard() == DISABLE_COMMUNITY_GUARD
        assert governanceCommunityGuarded.getCommunityKey() == cf.COMMUNITY_KEY
        # Enable again
        governanceCommunityGuarded.setCommunityGuard(
            ENABLE_COMMUNITY_GUARD, {"from": cf.COMMUNITY_KEY}
        )
        assert governanceCommunityGuarded.getCommunityGuard() == ENABLE_COMMUNITY_GUARD
        assert governanceCommunityGuarded.getCommunityKey() == cf.COMMUNITY_KEY


def test_updateCommunityKey(cf):
    governanceCommunityGuardedList = getgovernanceCommunityGuardedList(cf)
    for governanceCommunityGuarded in governanceCommunityGuardedList:
        with reverts(REV_MSG_GOV_NOT_COMMUNITY):
            governanceCommunityGuarded.updateCommunityKey(ZERO_ADDR, {"from": cf.ALICE})
        with reverts(REV_MSG_NZ_ADDR):
            governanceCommunityGuarded.updateCommunityKey(
                ZERO_ADDR, {"from": cf.COMMUNITY_KEY}
            )
        governanceCommunityGuarded.updateCommunityKey(
            cf.COMMUNITY_KEY_2, {"from": cf.COMMUNITY_KEY}
        )
        assert governanceCommunityGuarded.getCommunityKey() == cf.COMMUNITY_KEY_2
        assert governanceCommunityGuarded.getCommunityGuard() == ENABLE_COMMUNITY_GUARD

        # Ensure that new community address can disable community Guard and the old one cannot
        with reverts(REV_MSG_GOV_NOT_COMMUNITY):
            governanceCommunityGuarded.setCommunityGuard(
                DISABLE_COMMUNITY_GUARD, {"from": cf.COMMUNITY_KEY}
            )
        governanceCommunityGuarded.setCommunityGuard(
            DISABLE_COMMUNITY_GUARD, {"from": cf.COMMUNITY_KEY_2}
        )
        assert governanceCommunityGuarded.getCommunityGuard() == DISABLE_COMMUNITY_GUARD


def getgovernanceCommunityGuardedList(cf):
    return [cf.stakeManager, cf.vault]
