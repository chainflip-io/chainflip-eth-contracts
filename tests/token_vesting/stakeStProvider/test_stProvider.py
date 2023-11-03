from consts import *
from brownie import reverts
from shared_tests_tokenVesting import *


def test_stakeToStProvider(addrs, tokenVestingStaking, cf, mockStProvider):
    tv, _, _, total = tokenVestingStaking
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


def test_rev_sender(addrs, tokenVestingStaking):
    tv, _, _, total = tokenVestingStaking
    with reverts(REV_MSG_NOT_BENEFICIARY):
        tv.stakeToStProvider(total, {"from": addrs.DEPLOYER})
    with reverts(REV_MSG_NOT_BENEFICIARY):
        tv.unstakeFromStProvider(0, {"from": addrs.DEPLOYER})
    with reverts(REV_MSG_NOT_BENEFICIARY):
        tv.claimStProviderRewards(0, {"from": addrs.DEPLOYER})


def test_rev_amount(addrs, tokenVestingStaking):
    tv, _, _, total = tokenVestingStaking
    with reverts(REV_MSG_ERC20_EXCEED_BAL):
        tv.stakeToStProvider(total + 1, {"from": addrs.BENEFICIARY})

    with reverts(REV_MSG_ERC20_EXCEED_BAL):
        tv.unstakeFromStProvider(1, {"from": addrs.BENEFICIARY})


def test_stake_rev_revoked(addrs, tokenVestingStaking, cf):
    tv, _, _, _ = tokenVestingStaking

    tv.revoke(cf.flip, {"from": addrs.REVOKER})
    with reverts(REV_MSG_TOKEN_REVOKED):
        tv.stakeToStProvider(1, {"from": addrs.BENEFICIARY})


def test_unstake_rev_revoked(addrs, tokenVestingStaking, mockStProvider):
    tv, _, _, _ = tokenVestingStaking
    stFLIP, _, _, _ = mockStProvider

    tv.revoke(stFLIP, {"from": addrs.REVOKER})

    with reverts(REV_MSG_TOKEN_REVOKED):
        tv.unstakeFromStProvider(1, {"from": addrs.BENEFICIARY})


def test_claim_rev_revoked(addrs, tokenVestingStaking, mockStProvider):
    tv, _, _, _ = tokenVestingStaking
    stFLIP, _, _, _ = mockStProvider

    tv.revoke(stFLIP, {"from": addrs.REVOKER})

    with reverts(REV_MSG_TOKEN_REVOKED):
        tv.claimStProviderRewards(1, {"from": addrs.BENEFICIARY})


def test_unstakeFromStProvider(addrs, tokenVestingStaking, cf, mockStProvider):
    tv, _, _, total = tokenVestingStaking
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


## Claim rewards flow possibilities
## 1. increment stake (staked 100, unstaked 0, balance 100)
## 2. earn rewards    (staked 100, unstaked 0, balance 103)
## 3. claim rewards   (staked 100, unstaked 0, balance 100) 103 + 0 - 100 = 3
## 4. receive 3 stflip
##
## 1. stake            (staked 100, unstaked 0, balance 100)
## 2. earn rewards     (staked 100, unstaked 0, balance 103)
## 3. unstake all      (staked 100, unstaked 103, balance 0)
## 4. claim underflows (staked 100, unstaked 103, balance 0) 0 + 103 - 100 = 3
## 5. Need to have stflip to claim
## 1. stake            (staked 100, unstaked 0, balance 100)
## 2. get slashed      (staked 100, unstaked 0, balance 95)
## 3. unstake all      (staked 100, unstaked 0, balance 95)
## 4. claim underflows (staked 100, unstaked 0, balance 95) 95 + 0 - 100 = -5
## 5. must earn 5 stflip first before earning claimable rewards
##
## 1. stake            (staked 100, unstaked 0, balance 100)
## 2. earn rewards     (staked 100, unstaked 0, balance 103)
## 3. unstake half     (staked 50, unstaked 53, balance 50)
## 4. claim rewards   (staked 50, unstaked 53, balance 50) 50 + 53 - 50 = 3
## 5. Receive 3 stflip


def test_stProviderClaimRewards(addrs, tokenVestingStaking, cf, mockStProvider):
    tv, _, _, total = tokenVestingStaking
    stFLIP, minter, _, _ = mockStProvider
    reward_amount = 100 * 10**18

    cf.flip.approve(minter, 2**256 - 1, {"from": addrs.DEPLOYER})
    minter.mint(addrs.DEPLOYER, reward_amount, {"from": addrs.DEPLOYER})

    assert cf.flip.balanceOf(tv) == total
    assert stFLIP.balanceOf(tv) == 0
    assert tv.stTokenStaked() == 0
    assert tv.stTokenUnstaked() == 0

    tv.stakeToStProvider(total, {"from": addrs.BENEFICIARY})

    assert cf.flip.balanceOf(tv) == 0
    assert stFLIP.balanceOf(tv) == total
    assert tv.stTokenStaked() == total
    assert tv.stTokenUnstaked() == 0

    stFLIP.transfer(tv, reward_amount, {"from": addrs.DEPLOYER})  # earn rewards

    assert cf.flip.balanceOf(tv) == 0
    assert stFLIP.balanceOf(tv) == total + reward_amount
    assert tv.stTokenStaked() == total
    assert tv.stTokenUnstaked() == 0

    tv.claimStProviderRewards(reward_amount, {"from": addrs.BENEFICIARY})

    assert cf.flip.balanceOf(tv) == 0
    assert stFLIP.balanceOf(tv) == total
    assert tv.stTokenStaked() == total
    assert tv.stTokenUnstaked() == 0
    assert stFLIP.balanceOf(addrs.BENEFICIARY) == reward_amount


def test_stProviderClaimRewardsInsufficientStflip(
    addrs, tokenVestingStaking, cf, mockStProvider
):
    tv, _, _, total = tokenVestingStaking
    stFLIP, minter, _, _ = mockStProvider
    reward_amount = 100 * 10**18

    cf.flip.approve(minter, 2**256 - 1, {"from": addrs.DEPLOYER})
    minter.mint(addrs.DEPLOYER, reward_amount, {"from": addrs.DEPLOYER})

    assert cf.flip.balanceOf(tv) == total
    assert stFLIP.balanceOf(tv) == 0
    assert tv.stTokenStaked() == 0
    assert tv.stTokenUnstaked() == 0

    tv.stakeToStProvider(total, {"from": addrs.BENEFICIARY})

    assert cf.flip.balanceOf(tv) == 0
    assert stFLIP.balanceOf(tv) == total
    assert tv.stTokenStaked() == total
    assert tv.stTokenUnstaked() == 0

    stFLIP.transfer(tv, reward_amount, {"from": addrs.DEPLOYER})  # earn rewards

    assert cf.flip.balanceOf(tv) == 0
    assert stFLIP.balanceOf(tv) == total + reward_amount
    assert tv.stTokenStaked() == total
    assert tv.stTokenUnstaked() == 0

    tv.unstakeFromStProvider(total + reward_amount, {"from": addrs.BENEFICIARY})

    assert cf.flip.balanceOf(tv) == 0
    assert stFLIP.balanceOf(tv) == 0
    assert tv.stTokenStaked() == total
    assert tv.stTokenUnstaked() == total + reward_amount

    with reverts(REV_MSG_ERC20_EXCEED_BAL):
        tv.claimStProviderRewards(reward_amount, {"from": addrs.BENEFICIARY})


def test_stProviderClaimRewardsSlash(addrs, tokenVestingStaking, cf, mockStProvider):
    tv, _, _, total = tokenVestingStaking
    stFLIP, _, _, _ = mockStProvider
    slash_amount = 100 * 10**18

    assert cf.flip.balanceOf(tv) == total
    assert stFLIP.balanceOf(tv) == 0
    assert tv.stTokenStaked() == 0
    assert tv.stTokenUnstaked() == 0

    tv.stakeToStProvider(total, {"from": addrs.BENEFICIARY})

    assert cf.flip.balanceOf(tv) == 0
    assert stFLIP.balanceOf(tv) == total
    assert tv.stTokenStaked() == total
    assert tv.stTokenUnstaked() == 0

    stFLIP.mockSlash(tv, slash_amount, {"from": addrs.DEPLOYER})

    assert cf.flip.balanceOf(tv) == 0
    assert stFLIP.balanceOf(tv) == total - slash_amount
    assert tv.stTokenStaked() == total
    assert tv.stTokenUnstaked() == 0

    tv.unstakeFromStProvider(total - slash_amount, {"from": addrs.BENEFICIARY})

    assert cf.flip.balanceOf(tv) == 0
    assert stFLIP.balanceOf(tv) == 0
    assert tv.stTokenStaked() == total
    assert tv.stTokenUnstaked() == total - slash_amount

    with reverts(REV_MSG_INTEGER_OVERFLOW):
        tv.claimStProviderRewards(2**256 - 1, {"from": addrs.BENEFICIARY})


def test_stProviderRewards_release(addrs, tokenVestingStaking, cf, mockStProvider):
    tv, stakingVestingEnd, end, total = tokenVestingStaking
    stFLIP, minter, _, _ = mockStProvider
    reward_amount = total

    cf.flip.approve(minter, 2**256 - 1, {"from": addrs.DEPLOYER})
    minter.mint(addrs.DEPLOYER, reward_amount, {"from": addrs.DEPLOYER})

    flipStaked = total // 3
    flipInContract = total - flipStaked
    tv.stakeToStProvider(flipStaked, {"from": addrs.BENEFICIARY})
    stFlipInContract = flipStaked

    # Earn rewards
    stFLIP.transfer(tv, reward_amount, {"from": addrs.DEPLOYER})
    stFlipInContract += reward_amount

    # Approximately into the middle of the vesting period
    chain.sleep(stakingVestingEnd + (end - stakingVestingEnd) // 2 - getChainTime())

    # The vested percentage of FLIP and stFLIP can be released.
    tx = tv.release(cf.flip, {"from": addrs.BENEFICIARY})
    releasedAmount = tx.events["TokensReleased"]["amount"]
    assert flipInContract // 2 <= releasedAmount <= flipInContract * 1.01 // 2

    tx = tv.release(stFLIP, {"from": addrs.BENEFICIARY})
    releasedAmount = tx.events["TokensReleased"]["amount"]
    assert stFlipInContract // 2 <= releasedAmount <= stFlipInContract * 1.01 // 2
