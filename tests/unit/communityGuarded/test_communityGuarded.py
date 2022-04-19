from consts import *
from brownie import reverts


def test_constructor(cf):
    communityGuarded_list = [cf.stakeManager, cf.vault]
    for communityGuarded in communityGuarded_list:
        assert communityGuarded.getCommunityKey() == cf.COMMUNITY_KEY
        assert communityGuarded.getCommunityGuard() == ENABLE_COMMUNITY_GUARD


def test_constructor_deploy(cf, Vault, StakeManager):
    with reverts(REV_MSG_NZ_ADDR):
        cf.vault = cf.DEPLOYER.deploy(Vault, cf.keyManager, ZERO_ADDR)

    with reverts(REV_MSG_NZ_ADDR):
        cf.stakeManager = cf.DEPLOYER.deploy(
            StakeManager, cf.keyManager, MIN_STAKE, ZERO_ADDR
        )


def test_setCommunityGuard(cf):
    communityGuarded_list = [cf.stakeManager, cf.vault]
    for communityGuarded in communityGuarded_list:
        with reverts(REV_MSG_NOT_COMMUNITY):
            communityGuarded.setCommunityGuard(
                DISABLE_COMMUNITY_GUARD, {"from": cf.ALICE}
            )
        # Setting Guard to the same value to ensure that nothing weird happens
        communityGuarded.setCommunityGuard(
            ENABLE_COMMUNITY_GUARD, {"from": cf.COMMUNITY_KEY}
        )
        assert communityGuarded.getCommunityGuard() == ENABLE_COMMUNITY_GUARD
        assert communityGuarded.getCommunityKey() == cf.COMMUNITY_KEY
        # Disable Guard
        communityGuarded.setCommunityGuard(
            DISABLE_COMMUNITY_GUARD, {"from": cf.COMMUNITY_KEY}
        )
        assert communityGuarded.getCommunityGuard() == DISABLE_COMMUNITY_GUARD
        assert communityGuarded.getCommunityKey() == cf.COMMUNITY_KEY
        # Enable again
        communityGuarded.setCommunityGuard(
            ENABLE_COMMUNITY_GUARD, {"from": cf.COMMUNITY_KEY}
        )
        assert communityGuarded.getCommunityGuard() == ENABLE_COMMUNITY_GUARD
        assert communityGuarded.getCommunityKey() == cf.COMMUNITY_KEY


def test_updateCommunityKey(cf):
    communityGuarded_list = [cf.stakeManager, cf.vault]
    for communityGuarded in communityGuarded_list:
        with reverts(REV_MSG_NOT_COMMUNITY):
            communityGuarded.updateCommunityKey(ZERO_ADDR, {"from": cf.ALICE})
        with reverts(REV_MSG_NZ_ADDR):
            communityGuarded.updateCommunityKey(ZERO_ADDR, {"from": cf.COMMUNITY_KEY})
        communityGuarded.updateCommunityKey(
            cf.COMMUNITY_KEY_2, {"from": cf.COMMUNITY_KEY}
        )
        assert communityGuarded.getCommunityKey() == cf.COMMUNITY_KEY_2
        assert communityGuarded.getCommunityGuard() == ENABLE_COMMUNITY_GUARD

        # Ensure that new community address can disable community Guard and the old one cannot
        with reverts(REV_MSG_NOT_COMMUNITY):
            communityGuarded.setCommunityGuard(
                DISABLE_COMMUNITY_GUARD, {"from": cf.COMMUNITY_KEY}
            )
        communityGuarded.setCommunityGuard(
            DISABLE_COMMUNITY_GUARD, {"from": cf.COMMUNITY_KEY_2}
        )
        assert communityGuarded.getCommunityGuard() == DISABLE_COMMUNITY_GUARD
