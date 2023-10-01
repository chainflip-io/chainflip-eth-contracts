from consts import *
from brownie import reverts
from shared_tests_tokenVesting import *


def test_stakeAggregateStProvider(addrs, tokenVestingStaking, cf, mockStProvider):
    tv, _, total = tokenVestingStaking
    stFLIP, _, _, staking_address, aggregator = mockStProvider

    mockMultiplier = 11 * 10**17
    expectedReceived = int(
        int(int(total) * int(mockMultiplier)) // 10**18
    )  # i was getting weird rounding issues. not sure what the best practice is here in brownie
    aggregator.setMockMultiplier(mockMultiplier)
    print(
        "balances",
        cf.flip.balanceOf(tv),
        stFLIP.balanceOf(tv),
        cf.flip.balanceOf(staking_address),
        stFLIP.balanceOf(staking_address),
    )

    assert cf.flip.balanceOf(tv) == total
    assert stFLIP.balanceOf(tv) == 0
    assert cf.flip.balanceOf(staking_address) == 0
    assert stFLIP.balanceOf(staking_address) == 0
    assert tv.stTokenStaked() == 0
    assert tv.stTokenUnstaked() == 0

    tv.aggregateStakeToStProvider(total, total, 0, {"from": addrs.BENEFICIARY})

    print(
        "balances",
        cf.flip.balanceOf(tv),
        stFLIP.balanceOf(tv),
        cf.flip.balanceOf(staking_address),
        stFLIP.balanceOf(staking_address),
    )

    assert cf.flip.balanceOf(tv) == 0
    assert stFLIP.balanceOf(tv) == expectedReceived
    assert cf.flip.balanceOf(staking_address) == total
    assert stFLIP.balanceOf(staking_address) == 0
    assert tv.stTokenStaked() == expectedReceived
    assert tv.stTokenUnstaked() == 0


def test_unstakeAggregateStProvider(addrs, tokenVestingStaking, cf, mockStProvider):
    tv, _, total = tokenVestingStaking
    stFLIP, _, _, staking_address, aggregator = mockStProvider

    mockMultiplier = 11 * 10**17
    expectedReceived = int(
        int(int(total) * (2 * 10**18 - int(mockMultiplier))) // 10**18
    )  # i was getting weird rounding issues. not sure what the best practice is here in brownie
    aggregator.setMockMultiplier(mockMultiplier)

    tv.stakeToStProvider(total, {"from": addrs.BENEFICIARY})

    print(
        "balances",
        cf.flip.balanceOf(tv),
        stFLIP.balanceOf(tv),
        cf.flip.balanceOf(staking_address),
        stFLIP.balanceOf(staking_address),
    )

    assert cf.flip.balanceOf(tv) == 0
    assert stFLIP.balanceOf(tv) == total
    assert cf.flip.balanceOf(staking_address) == total
    assert stFLIP.balanceOf(staking_address) == 0
    assert tv.stTokenStaked() == total
    assert tv.stTokenUnstaked() == 0

    tv.aggregateUnstakeToStProvider(0, 0, total, 0, {"from": addrs.BENEFICIARY})

    print(
        "balances",
        cf.flip.balanceOf(tv),
        stFLIP.balanceOf(tv),
        cf.flip.balanceOf(staking_address),
        stFLIP.balanceOf(staking_address),
    )

    assert cf.flip.balanceOf(tv) == expectedReceived
    assert stFLIP.balanceOf(tv) == 0
    assert cf.flip.balanceOf(staking_address) == total - expectedReceived
    assert stFLIP.balanceOf(staking_address) == 0
    assert tv.stTokenStaked() == total
    assert tv.stTokenUnstaked() == total


def test_stProviderClaimRewards(addrs, tokenVestingStaking, cf, mockStProvider):
    tv, _, total = tokenVestingStaking
    stFLIP, minter, _, staking_address, aggregator = mockStProvider
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

    tv.claimStProviderRewards(
        addrs.BENEFICIARY, reward_amount, {"from": addrs.BENEFICIARY}
    )

    assert cf.flip.balanceOf(tv) == 0
    assert stFLIP.balanceOf(tv) == total
    assert tv.stTokenStaked() == total
    assert tv.stTokenUnstaked() == 0
    assert stFLIP.balanceOf(addrs.BENEFICIARY) == reward_amount
