from consts import *
from brownie import reverts
from shared_tests_tokenVesting import *


def test_stakeToStProvider(addrs, tokenVestingStaking, cf, mockStProvider):
    tv, _, total = tokenVestingStaking
    stFLIP, _, _, staking_address = mockStProvider

    assert cf.flip.balanceOf(tv) == total
    assert stFLIP.balanceOf(tv) == 0
    assert cf.flip.balanceOf(staking_address) == 0
    assert stFLIP.balanceOf(staking_address) == 0
    tv.stakeToStProvider(total, {"from": addrs.BENEFICIARY})
    assert cf.flip.balanceOf(tv) == 0
    assert stFLIP.balanceOf(tv) == total
    assert cf.flip.balanceOf(staking_address) == total
    assert stFLIP.balanceOf(staking_address) == 0


def test_stake_unstake_rev_sender(addrs, tokenVestingStaking):
    tv, _, total = tokenVestingStaking
    with reverts(REV_MSG_NOT_BENEFICIARY):
        tv.stakeToStProvider(total, {"from": addrs.DEPLOYER})
    with reverts(REV_MSG_NOT_BENEFICIARY):
        tv.unstakeFromStProvider(0, {"from": addrs.DEPLOYER})


def test_stake_unstake_rev_amount(addrs, tokenVestingStaking):
    tv, _, total = tokenVestingStaking
    with reverts(REV_MSG_ERC20_EXCEED_BAL):
        tv.stakeToStProvider(total + 1, {"from": addrs.BENEFICIARY})

    with reverts(REV_MSG_ERC20_EXCEED_BAL):
        tv.unstakeFromStProvider(1, {"from": addrs.BENEFICIARY})


def test_stake_rev_revoked(addrs, tokenVestingStaking, cf):
    tv, _, _ = tokenVestingStaking

    tv.revoke(cf.flip, {"from": addrs.REVOKER})
    with reverts(REV_MSG_TOKEN_REVOKED):
        tv.stakeToStProvider(1, {"from": addrs.BENEFICIARY})


def test_unstake_rev_revoked(addrs, tokenVestingStaking, mockStProvider):
    tv, _, _ = tokenVestingStaking
    stFLIP, _, _, _ = mockStProvider

    tv.revoke(stFLIP, {"from": addrs.REVOKER})

    with reverts(REV_MSG_TOKEN_REVOKED):
        tv.unstakeFromStProvider(1, {"from": addrs.BENEFICIARY})


def test_unstakeFromStProvider(addrs, tokenVestingStaking, cf, mockStProvider):
    tv, _, total = tokenVestingStaking
    stFLIP, _, burner, staking_address = mockStProvider

    test_stakeToStProvider(addrs, tokenVestingStaking, cf, mockStProvider)

    tv.unstakeFromStProvider(total, {"from": addrs.BENEFICIARY})

    assert cf.flip.balanceOf(tv) == 0
    assert stFLIP.balanceOf(tv) == 0
    assert cf.flip.balanceOf(staking_address) == total
    assert stFLIP.balanceOf(staking_address) == 0

    ## Index from Burn array to redeem == 0
    burner.redeem(0, {"from": cf.ALICE})

    assert cf.flip.balanceOf(tv) == total
    assert stFLIP.balanceOf(tv) == 0
    assert cf.flip.balanceOf(staking_address) == 0
    assert stFLIP.balanceOf(staking_address) == 0
