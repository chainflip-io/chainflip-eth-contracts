from consts import *
from brownie import reverts


def test_setCommKeyWithCommKey(cf):
    governanceCommunityGuardedList = [cf.stakeManager, cf.vault]

    with reverts(REV_MSG_KEYMANAGER_NOT_COMMUNITY):
        cf.keyManager.setCommKeyWithCommKey(ZERO_ADDR, {"from": cf.ALICE})
    with reverts(REV_MSG_NZ_ADDR):
        cf.keyManager.setCommKeyWithCommKey(ZERO_ADDR, {"from": cf.COMMUNITY_KEY})

    tx = cf.keyManager.setCommKeyWithCommKey(
        cf.COMMUNITY_KEY_2, {"from": cf.COMMUNITY_KEY}
    )
    assert tx.events["CommKeySetByCommKey"][0].values() == (
        cf.COMMUNITY_KEY,
        cf.COMMUNITY_KEY_2,
    )

    for governanceCommunityGuarded in governanceCommunityGuardedList:
        assert governanceCommunityGuarded.getCommunityKey() == cf.COMMUNITY_KEY_2
        assert governanceCommunityGuarded.getCommunityGuard() == False

        # Ensure that new community address can disable community Guard and the old one cannot
        with reverts(REV_MSG_GOV_NOT_COMMUNITY):
            governanceCommunityGuarded.disableCommunityGuard({"from": cf.COMMUNITY_KEY})
        governanceCommunityGuarded.disableCommunityGuard({"from": cf.COMMUNITY_KEY_2})
        assert governanceCommunityGuarded.getCommunityGuard() == True
