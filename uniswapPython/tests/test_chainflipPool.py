import sys, os

from utilities import *
from brownie.test import given, strategy

sys.path.append(os.path.join(os.path.dirname(sys.path[0]), "contracts"))
from ChainflipPool import *
from Account import Ledger
import SwapMath
import TickMath

import pytest
import copy
import random

# NOTE: These tests are adapted from the original UniswapPool tests but chainging the range orders minted
# for limit orders. More tests have been added in order to test limit orders.


@pytest.fixture
def accounts(ledger):
    # return [ledger.accounts[account] for account in ledger.accounts.keys()]
    # list of raw addresses
    return list(ledger.accounts.keys())


# TODO: Improve this
@pytest.fixture
def ledger():
    # Fund them with infinite tokens
    account0 = [
        "ALICE",
        TEST_TOKENS,
        [MAX_INT256 // 100, MAX_INT256 // 100 // 100],
    ]  # LP0 - backup liquidity
    account1 = ["BOB", TEST_TOKENS, [MAX_INT256 // 100, MAX_INT256 // 100]]  # LP1
    account2 = ["CHARLIE", TEST_TOKENS, [1000, 2000]]  # Small amount
    account3 = [
        "DENICE",
        TEST_TOKENS,
        [expandTo18Decimals(10), expandTo18Decimals(10)],
    ]  # Swapper
    account4 = [
        "EVA",
        TEST_TOKENS,
        [MAX_INT256 // 100, MAX_INT256 // 100],
    ]  # LP Testing
    account5 = [
        "FINN",
        TEST_TOKENS,
        [MAX_INT256 // 100, MAX_INT256 // 100],
    ]  # LP Testing2
    ledger = Ledger([account0, account1, account2, account3, account4, account5])
    return ledger


def createPool(feeAmount, tickSpacing, ledger):
    feeAmount = feeAmount
    pool = ChainflipPool(TEST_TOKENS[0], TEST_TOKENS[1], feeAmount, tickSpacing, ledger)
    minTick = getMinTickLO(tickSpacing)
    maxTick = getMaxTickLO(tickSpacing)
    return pool, minTick, maxTick, feeAmount, tickSpacing


@pytest.fixture
def createPoolMedium(ledger):
    return createPool(FeeAmount.MEDIUM, TICK_SPACINGS[FeeAmount.MEDIUM], ledger)


@pytest.fixture
def createPoolLow(ledger):
    return createPool(FeeAmount.LOW, TICK_SPACINGS[FeeAmount.LOW], ledger)


@pytest.fixture
def initializedMediumPool(createPoolMedium, accounts):
    pool, minTick, maxTick, _, _ = createPoolMedium
    pool.initialize(encodePriceSqrt(1, 10))
    # pool.mint(accounts[0], minTick, maxTick, 3161)
    # In order to mimic the original tests, we provide liquidity from current tick to MAX tick
    # for each of the two assets. Doing two different roundings so both include current tick
    closeAligniniTickiRDown = pool.slot0.tick - 12  # -23016
    closeAligniniTickRUp = pool.slot0.tick + 48  # −22968

    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], maxTick, 3161)
    # 3162 to make it different
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], minTick, 3162)

    return *createPoolMedium, closeAligniniTickiRDown, closeAligniniTickRUp


@pytest.fixture
def initializedMediumPoolNoLO(createPoolMedium):
    pool, _, _, _, _ = createPoolMedium
    pool.initialize(encodePriceSqrt(1, 10))
    # pool.mint(accounts[0], minTick, maxTick, 3161)
    # In order to mimic the original tests, we provide liquidity from current tick to MAX tick
    # for each of the two assets. Doing two different roundings so both include current tick
    closeAligniniTickiRDown = pool.slot0.tick - 12  # -23016
    closeAligniniTickRUp = pool.slot0.tick + 48  # −22968

    return *createPoolMedium, closeAligniniTickiRDown, closeAligniniTickRUp


@pytest.fixture
def initializedLowPoolCollect(createPoolLow):
    pool, _, _, _, _ = createPoolLow
    pool.initialize(encodePriceSqrt(1, 1))
    return createPoolLow


def test_constructor(createPoolMedium):
    print("constructor initializes immutables")
    pool, _, _, _, _ = createPoolMedium
    assert pool.token0 == TEST_TOKENS[0]
    assert pool.token1 == TEST_TOKENS[1]
    assert pool.fee == FeeAmount.MEDIUM
    assert pool.tickSpacing == TICK_SPACINGS[FeeAmount.MEDIUM]


# Initialize
def test_fails_alreadyInitialized(createPoolMedium):
    print("fails if already initialized")
    pool, _, _, _, _ = createPoolMedium
    pool.initialize(encodePriceSqrt(1, 1))
    tryExceptHandler(pool.initialize, "AI", encodePriceSqrt(1, 1))


def test_fails_lowStartingPrice(createPoolMedium):
    pool, _, _, _, _ = createPoolMedium
    print("fails if already initialized")
    tryExceptHandler(pool.initialize, "R", 1)
    tryExceptHandler(pool.initialize, "R", TickMath.MIN_SQRT_RATIO - 1)


def test_fails_highStartingPrice(createPoolMedium):
    print("fails if already initialized")
    pool, _, _, _, _ = createPoolMedium
    tryExceptHandler(pool.initialize, "R", TickMath.MAX_SQRT_RATIO)
    tryExceptHandler(pool.initialize, "R", MAX_UINT160)


def test_initialize_MIN_SQRT_RATIO(createPoolMedium):
    print("can be initialized at MIN_SQRT_RATIO")
    pool, _, _, _, _ = createPoolMedium
    pool.initialize(TickMath.MIN_SQRT_RATIO)
    assert pool.slot0.tick == getMinTick(1)


def test_initialize_MAX_SQRT_RATIO_minusOne(createPoolMedium):
    print("can be initialized at MAX_SQRT_RATIO - 1")
    pool, _, _, _, _ = createPoolMedium
    pool.initialize(TickMath.MAX_SQRT_RATIO - 1)
    assert pool.slot0.tick == getMaxTick(1) - 1


def test_setInitialVariables(createPoolMedium):
    print("sets initial variables")
    pool, _, _, _, _ = createPoolMedium
    price = encodePriceSqrt(1, 2)
    pool.initialize(price)

    assert pool.slot0.sqrtPriceX96 == price
    assert pool.slot0.tick == -6932


# Mint


def test_trialmint(createPoolMedium, accounts):
    pool, minTick, maxTick, _, _ = createPoolMedium
    pool.initialize(encodePriceSqrt(1, 1))
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], minTick, 3161)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], maxTick, 3161)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], minTick, 3162)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], maxTick, 3162)


def test_initialize_10to1(createPoolMedium, accounts):
    pool, minTick, maxTick, _, _ = createPoolMedium
    pool.initialize(encodePriceSqrt(1, 10))
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], minTick, 3161)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], maxTick, 3161)


def test_fails_tick_ltMinTick(initializedMediumPool, accounts):
    print("fails if tickLower less than min Tick")
    pool, _, _, _, _, _, _ = initializedMediumPool
    tryExceptHandler(
        pool.mintLimitOrder, "TLM", TEST_TOKENS[0], accounts[0], -887273, 1
    )
    tryExceptHandler(
        pool.mintLimitOrder, "TLM", TEST_TOKENS[0], accounts[0], -887271, 1
    )
    tryExceptHandler(
        pool.mintLimitOrder, "TLM", TEST_TOKENS[0], accounts[0], -665456, 1
    )


def test_fails_tick_gtMaxTick(initializedMediumPool, accounts):
    print("fails if tickUpper greater than max Tick")
    pool, _, _, _, _, _, _ = initializedMediumPool
    tryExceptHandler(pool.mintLimitOrder, "TUM", TEST_TOKENS[0], accounts[0], 887273, 1)
    tryExceptHandler(pool.mintLimitOrder, "TUM", TEST_TOKENS[0], accounts[0], 887271, 1)
    tryExceptHandler(pool.mintLimitOrder, "TUM", TEST_TOKENS[0], accounts[0], 665457, 1)


def test_fails_amountGtMax(initializedMediumPool, accounts):
    print("fails if amount exceeds the max")
    pool, minTick, _, _, tickSpacing, _, _ = initializedMediumPool
    maxLiquidityGross = pool.maxLiquidityPerTick
    tryExceptHandler(
        pool.mintLimitOrder,
        "LO",
        TEST_TOKENS[0],
        accounts[0],
        minTick + tickSpacing,
        maxLiquidityGross + 1,
    )
    pool.mintLimitOrder(
        TEST_TOKENS[0],
        accounts[0],
        minTick + tickSpacing,
        maxLiquidityGross,
    )


def test_fails_totalAmountatTick_gtMAX(initializedMediumPool, accounts):
    print("fails if total amount at tick exceeds the max")
    pool, minTick, maxTick, _, tickSpacing, _, _ = initializedMediumPool
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], minTick + tickSpacing, 1000)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], maxTick - tickSpacing, 1000)
    maxLiquidityGross = pool.maxLiquidityPerTick
    tryExceptHandler(
        pool.mintLimitOrder,
        "LO",
        TEST_TOKENS[0],
        accounts[0],
        minTick + tickSpacing,
        maxLiquidityGross - 1000 + 1,
    )
    tryExceptHandler(
        pool.mintLimitOrder,
        "LO",
        TEST_TOKENS[0],
        accounts[0],
        maxTick - tickSpacing,
        maxLiquidityGross - 1000 + 1,
    )
    tryExceptHandler(
        pool.mintLimitOrder,
        "LO",
        TEST_TOKENS[0],
        accounts[0],
        maxTick - tickSpacing,
        maxLiquidityGross - 1000 + 1,
    )
    tryExceptHandler(
        pool.mintLimitOrder,
        "LO",
        TEST_TOKENS[0],
        accounts[0],
        minTick + tickSpacing,
        maxLiquidityGross - 1000 + 1,
    )
    pool.mintLimitOrder(
        TEST_TOKENS[0],
        accounts[0],
        minTick + tickSpacing,
        maxLiquidityGross - 1000,
    )

    pool.mintLimitOrder(
        TEST_TOKENS[0],
        accounts[0],
        maxTick - tickSpacing,
        maxLiquidityGross - 1000,
    )


def test_fails_zeroAmount(initializedMediumPool, accounts):
    print("fails if amount is zero")
    pool, minTick, maxTick, _, tickSpacing, _, _ = initializedMediumPool
    tryExceptHandler(
        pool.mintLimitOrder,
        "",
        TEST_TOKENS[0],
        accounts[0],
        minTick + tickSpacing,
        0,
    )


# Success cases


def test_initial_balances(initializedMediumPool):
    print("fails if amount is zero")
    pool, _, _, _, _, _, _ = initializedMediumPool
    # Limit order value
    assert pool.balances[pool.token0] == 3161
    # Limit order value
    assert pool.balances[pool.token1] == 3162


def test_mint_one_side(initializedMediumPool, accounts):
    print("mints one side")
    (
        pool,
        minTick,
        maxTick,
        _,
        _,
        closeIniTickRDown,
        closeIniTickRUp,
    ) = initializedMediumPool

    assert pool.balances[pool.token0] == 3161
    assert pool.balances[pool.token1] == 3162

    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], closeIniTickRDown, 3161)

    assert pool.balances[pool.token0] == 3161 * 2
    assert pool.balances[pool.token1] == 3162

    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], closeIniTickRUp, 3162)
    assert pool.balances[pool.token0] == 3161 * 2
    assert pool.balances[pool.token1] == 3162 * 2


def test_initialTick(initializedMediumPool):
    print("fails if amount is zero")
    pool, _, _, _, _, _, _ = initializedMediumPool
    # Limit orders have not altered the tick
    assert pool.slot0.tick == -23028


# Above current tick
def test_transferToken0_only(initializedMediumPool, accounts):
    print("transferToken0 only")
    pool, _, _, _, _, _, _ = initializedMediumPool
    amount1Before = pool.balances[TEST_TOKENS[1]]
    amount0 = pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], -22980, 10000)
    assert amount0 != 0
    assert pool.balances[TEST_TOKENS[1]] == amount1Before
    assert pool.balances[pool.token0] == 3161 + 10000


def test_maxTick_maxLeverage(initializedMediumPool, accounts):
    print("max tick with max leverage")
    pool, _, maxTick, _, tickSpacing, _, _ = initializedMediumPool
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], maxTick, 2**102)
    assert pool.balances[pool.token0] == 3161 + 2**102
    assert pool.balances[pool.token1] == 3162


def test_maxTick(initializedMediumPool, accounts):
    print("works for max tick")
    pool, _, maxTick, _, _, _, _ = initializedMediumPool
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], maxTick, 10000)
    assert pool.balances[pool.token0] == 3161 + 10000
    assert pool.balances[pool.token1] == 3162


def test_remove_aboveCurrentPrice_token0(initializedMediumPool, accounts):
    print("removing works")
    pool, _, _, _, _, _, _ = initializedMediumPool
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], -240, 10000)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], 0, 10001)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], -240, 10000)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], 0, 10001)
    (_, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[0], -240, MAX_UINT128, MAX_UINT128
    )
    assert amount0 == 10000
    assert amount1 == 0
    (_, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[0], 0, MAX_UINT128, MAX_UINT128
    )
    assert amount0 == 10001
    assert amount1 == 0


def test_remove_aboveCurrentPrice_token1(initializedMediumPool, accounts):
    print("removing works")
    pool, _, _, _, _, _, _ = initializedMediumPool
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], -240, 10000)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], 0, 10001)
    pool.burnLimitOrder(TEST_TOKENS[1], accounts[0], -240, 10000)
    pool.burnLimitOrder(TEST_TOKENS[1], accounts[0], 0, 10001)
    (_, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[1], -240, MAX_UINT128, MAX_UINT128
    )
    assert amount0 == 0
    assert amount1 == 10000
    (_, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[1], 0, MAX_UINT128, MAX_UINT128
    )
    assert amount0 == 0
    assert amount1 == 10001


def test_addLiquidity_toLiquidityLeft(initializedMediumPool, accounts):
    print("addLiquidity to liquidity left")
    pool, _, _, _, tickSpacing, _, _ = initializedMediumPool
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], -240, 100)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], 0, 100)
    assert pool.ticksLimitTokens0[-240].liquidityLeft == 100
    assert pool.ticksLimitTokens0[0].liquidityLeft == 100
    # No liquidityLeft === tick doesn't exist
    assert not pool.ticksLimitTokens0.__contains__(tickSpacing)
    assert not pool.ticksLimitTokens0.__contains__(tickSpacing * 2)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], -240, 150)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], tickSpacing, 150)
    assert pool.ticksLimitTokens0[-240].liquidityLeft == 250
    assert pool.ticksLimitTokens0[0].liquidityLeft == 100
    assert pool.ticksLimitTokens0[tickSpacing].liquidityLeft == 150
    # No liquidityLeft === tick doesn't exist
    assert not pool.ticksLimitTokens0.__contains__(tickSpacing * 2)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], 0, 60)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], tickSpacing * 2, 60)
    assert pool.ticksLimitTokens0[-240].liquidityLeft == 250
    assert pool.ticksLimitTokens0[0].liquidityLeft == 160
    assert pool.ticksLimitTokens0[tickSpacing].liquidityLeft == 150
    assert pool.ticksLimitTokens0[tickSpacing * 2].liquidityLeft == 60


def test_removeLiquidity_fromLiquidityLeft(initializedMediumPool, accounts):
    print("removes liquidity from liquidityLeft")
    pool, _, _, _, _, _, _ = initializedMediumPool
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], -240, 100)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], 0, 40)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], -240, 90)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], 0, 30)

    assert pool.ticksLimitTokens0[-240].liquidityLeft == 10
    assert pool.ticksLimitTokens0[0].liquidityLeft == 10

    assert (
        pool.limitOrders[getLimitPositionKey(accounts[0], -240, True)].tokensOwed0 == 90
    )
    assert pool.limitOrders[getLimitPositionKey(accounts[0], 0, True)].tokensOwed0 == 30

    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], -240, 100)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], 0, 40)
    pool.burnLimitOrder(TEST_TOKENS[1], accounts[0], -240, 90)
    pool.burnLimitOrder(TEST_TOKENS[1], accounts[0], 0, 30)

    assert pool.ticksLimitTokens0[-240].liquidityLeft == 10
    assert pool.ticksLimitTokens0[0].liquidityLeft == 10

    assert (
        pool.limitOrders[getLimitPositionKey(accounts[0], -240, True)].tokensOwed0 == 90
    )
    assert pool.limitOrders[getLimitPositionKey(accounts[0], 0, True)].tokensOwed0 == 30


def test_clearTickLower_ifLastPositionRemoved(initializedMediumPool, accounts):
    print("clears tick lower if last position is removed")
    pool, _, _, _, _, _, _ = initializedMediumPool
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], -240, 100)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], 0, 100)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], -240, 100)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], 0, 100)
    # tick cleared == not in ticks
    assert not pool.ticksLimitTokens0.__contains__(-240)
    assert not pool.ticksLimitTokens0.__contains__(0)

    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], -240, 100)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], 0, 100)
    pool.burnLimitOrder(TEST_TOKENS[1], accounts[0], -240, 100)
    pool.burnLimitOrder(TEST_TOKENS[1], accounts[0], 0, 100)
    # tick cleared == not in ticks
    assert not pool.ticksLimitTokens1.__contains__(-240)
    assert not pool.ticksLimitTokens1.__contains__(0)


def test_clearTick_ifLastPositionRemoved(initializedMediumPool, accounts):
    print("clears tick upper if last position is removed")
    pool, _, _, _, _, _, _ = initializedMediumPool
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], 0, 100)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], 0, 100)
    # tick cleared == not in ticks
    assert not pool.ticksLimitTokens0.__contains__(0)

    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], -240, 100)
    pool.burnLimitOrder(TEST_TOKENS[1], accounts[0], -240, 100)
    # tick cleared == not in ticks
    assert not pool.ticksLimitTokens1.__contains__(0)


def test_clearsTick_ifNotUsed(initializedMediumPool, accounts):
    print("only clears the tick that is not used at all")
    pool, _, _, _, tickSpacing, _, _ = initializedMediumPool
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], -240, 100)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], 0, 100)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[1], -tickSpacing, 250)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[1], 0, 250)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], -240, 100)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], 0, 100)
    # tick cleared == not in ticks
    assert not pool.ticksLimitTokens0.__contains__(-240)
    tickInfo = pool.ticksLimitTokens0[-tickSpacing]
    assert tickInfo.liquidityLeft == 250
    assert tickInfo.feeGrowthInsideX128 == 0

    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], -240, 100)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], 0, 100)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[1], -tickSpacing, 250)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[1], 0, 250)
    pool.burnLimitOrder(TEST_TOKENS[1], accounts[0], -240, 100)
    pool.burnLimitOrder(TEST_TOKENS[1], accounts[0], 0, 100)
    # tick cleared == not in ticks
    assert not pool.ticksLimitTokens1.__contains__(-240)
    tickInfo = pool.ticksLimitTokens1[-tickSpacing]
    assert tickInfo.liquidityLeft == 250
    assert tickInfo.feeGrowthInsideX128 == 0


# # Including current price
# def test_transferCurrentPriceTokens(initializedMediumPool, accounts):
#     print("price within range: transfers current price of both tokens")
#     (
#         pool,
#         minTick,
#         maxTick,
#         _,
#         tickSpacing,
#         closeIniTickRDown,
#         closeIniTickRUp,
#     ) = initializedMediumPool
#     amount0 = pool.mintLimitOrder(
#         TEST_TOKENS[0], accounts[0], closeIniTickRDown, maxTick - tickSpacing, 100
#     )
#     amount1 = pool.mintLimitOrder(
#         TEST_TOKENS[1], accounts[0], minTick + tickSpacing, closeIniTickRUp, 100
#     )

#     assert amount0 == 317
#     assert amount1 == 32
#     assert pool.balances[pool.token0] == 3161 + 317
#     # Limit original: 1000
#     assert pool.balances[pool.token1] == 3162 + 32


# def test_initializes_lowerTick(initializedMediumPool, accounts):
#     print("initializes lower tick")
#     pool, minTick, maxTick, _, tickSpacing, _, _ = initializedMediumPool
#     pool.mintLimitOrder(
#         TEST_TOKENS[0], accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 100
#     )
#     liquidityGross = pool.ticksLimitTokens0[minTick + tickSpacing].liquidityGross
#     assert liquidityGross == 100

#     pool.mintLimitOrder(
#         TEST_TOKENS[1], accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 100
#     )
#     liquidityGross = pool.ticksLimitTokens1[minTick + tickSpacing].liquidityGross
#     assert liquidityGross == 100


# def test_initializes_upperTick(initializedMediumPool, accounts):
#     print("initializes upper tick")
#     pool, minTick, maxTick, _, tickSpacing, _, _ = initializedMediumPool
#     pool.mintLimitOrder(
#         TEST_TOKENS[0], accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 100
#     )
#     liquidityGross = pool.ticksLimitTokens0[maxTick - tickSpacing].liquidityGross
#     assert liquidityGross == 100

#     pool.mintLimitOrder(
#         TEST_TOKENS[1], accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 100
#     )
#     liquidityGross = pool.ticksLimitTokens1[maxTick - tickSpacing].liquidityGross
#     assert liquidityGross == 100


# def test_works_minMaxTick(initializedMediumPool, accounts):
#     print("works for min/ max tick")
#     (
#         pool,
#         minTick,
#         maxTick,
#         _,
#         _,
#         closeIniTickRDown,
#         closeIniTickRUp,
#     ) = initializedMediumPool
#     amount0 = pool.mintLimitOrder(
#         TEST_TOKENS[0], accounts[0], closeIniTickRDown, maxTick, 10000
#     )
#     # Original range = 31623
#     assert amount0 == 31644
#     assert pool.balances[pool.token0] == 3161 + 31644
#     assert pool.balances[pool.token1] == 3162
#     amount1 = pool.mintLimitOrder(
#         TEST_TOKENS[1], accounts[0], minTick, closeIniTickRUp, 10000
#     )
#     assert amount0 == 31644
#     # Original range = 3170
#     assert amount1 == 3170
#     assert pool.balances[pool.token0] == 3161 + 31644
#     assert pool.balances[pool.token1] == 3162 + 3170


def test_removing_includesCurrentPrice(initializedMediumPool, accounts):
    print("removing works")
    pool, minTick, maxTick, _, tickSpacing, _, _ = initializedMediumPool
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], minTick + tickSpacing, 100)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], maxTick - tickSpacing, 101)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], minTick + tickSpacing, 100)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], maxTick - tickSpacing, 101)

    (_, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[0], minTick + tickSpacing, MAX_UINT128, MAX_UINT128
    )
    assert amount0 == 100
    assert amount1 == 0

    (_, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[0], maxTick - tickSpacing, MAX_UINT128, MAX_UINT128
    )

    assert amount0 == 101
    assert amount1 == 0


# # Below current price
# def test_transfer_onlyToken1(initializedMediumPool, accounts):
#     print("transfers token1 only")
#     pool, _, _, _, _, _, _ = initializedMediumPool
#     amount1 = pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], -46080, -23040, 10000)
#     assert amount1 == 2162
#     assert pool.balances[pool.token0] == 3161
#     # Original range = 2162
#     assert pool.balances[pool.token1] == 1000 + 2164


# def test_minTick_maxLeverage(initializedMediumPool, accounts):
#     print("min tick with max leverage")
#     pool, minTick, _, _, tickSpacing, _, _ = initializedMediumPool
#     pool.mintLimitOrder(
#         TEST_TOKENS[1], accounts[0], minTick, minTick + tickSpacing, 2**102
#     )
#     assert pool.balances[pool.token0] == 3161
#     # Original range = 828011520
#     assert pool.balances[pool.token1] == 1000 + 828011522


# def test_works_minTick(initializedMediumPool, accounts):
#     print("works for min tick")
#     pool, minTick, _, _, _, _, _ = initializedMediumPool
#     amount1 = pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], minTick, -23040, 10000)
#     assert amount1 == 3161
#     assert pool.balances[pool.token0] == 3161
#     # Original range = 3161
#     assert pool.balances[pool.token1] == 1000 + 3163


# #TODO: Add tests minting positions on the other side of the tick


def test_removing_belowCurrentPrice(initializedMediumPool, accounts):
    print("removing works")
    pool, _, _, _, _, _, _ = initializedMediumPool
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], -46080, 10000)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], -46020, 10001)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], -46080, 10000)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], -46020, 10001)

    (_, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[0], -46080, MAX_UINT128, MAX_UINT128
    )
    assert amount0 == 10000
    assert amount1 == 0

    (_, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[0], -46020, MAX_UINT128, MAX_UINT128
    )
    assert amount0 == 10001
    assert amount1 == 0


# -------------------------------------- Notes about fees --------------------------------------
# For protocol fees it doesn't matter the position's liquidity since it only depends on amountIn.
# For growth fees, it is linear depending on the liquidity. However, feeGrowthInsideX128 is per
# unit of liquidity so it will depend on the positions liquidity. However, when collecting, the
# final amount should be the same (feeGrowthInsideX128 * positionLiquid).
# Also, position with TEST_TOKENS[0] will accrue growth fees in token1 (swaps oneForZero) while
# TEST_TOKENS[1] will accrue fees in token0 (swaps zeroForOne).
# ----------------------------------------------------------------------------------------------


def test_fees_duringSwap(initializedMediumPool, accounts):
    print("protocol fees accumulate as expected during swap")
    (
        pool,
        minTick,
        maxTick,
        _,
        tickSpacing,
        closeIniTickRDown,
        closeIniTickRUp,
    ) = initializedMediumPool
    pool.setFeeProtocol(6, 6)

    pool.mintLimitOrder(
        TEST_TOKENS[0],
        accounts[0],
        closeIniTickRDown,
        expandTo18Decimals(1),
    )

    pool.mintLimitOrder(
        TEST_TOKENS[1],
        accounts[0],
        closeIniTickRUp,
        expandTo18Decimals(1),
    )

    swapExact0For1(pool, expandTo18Decimals(1) // 10, accounts[0], None)
    swapExact1For0(pool, expandTo18Decimals(1) // 100, accounts[0], None)

    assert pool.protocolFees.token0 == 50000000000000
    assert pool.protocolFees.token1 == 5000000000000


def test_protectedPositions_beforefeesAreOn(initializedMediumPool, accounts):
    print("positions are protected before protocol fee is turned on")
    (
        pool,
        minTick,
        maxTick,
        _,
        tickSpacing,
        closeIniTickRDown,
        closeIniTickRUp,
    ) = initializedMediumPool

    pool.mintLimitOrder(
        TEST_TOKENS[0],
        accounts[0],
        closeIniTickRDown,
        expandTo18Decimals(1) // 2,
    )

    pool.mintLimitOrder(
        TEST_TOKENS[1],
        accounts[0],
        closeIniTickRUp,
        expandTo18Decimals(1) // 2,
    )

    swapExact0For1(pool, expandTo18Decimals(1) // 10, accounts[0], None)
    swapExact1For0(pool, expandTo18Decimals(1) // 100, accounts[0], None)

    assert pool.protocolFees.token0 == 0
    assert pool.protocolFees.token1 == 0


def test_notAllowPoke_uninitialized_position(initializedMediumPool, accounts):
    print("poke is not allowed on uninitialized position")
    (
        pool,
        minTick,
        maxTick,
        _,
        tickSpacing,
        closeIniTickRDown,
        closeIniTickRUp,
    ) = initializedMediumPool
    pool.mintLimitOrder(
        TEST_TOKENS[0], accounts[1], closeIniTickRDown, expandTo18Decimals(1)
    )
    pool.mintLimitOrder(
        TEST_TOKENS[1], accounts[1], closeIniTickRUp, expandTo18Decimals(1)
    )

    swapExact0For1(pool, expandTo18Decimals(1) // 10, accounts[0], None)
    swapExact1For0(pool, expandTo18Decimals(1) // 100, accounts[0], None)
    # Modified revert reason because a check is added in burn for uninitialized position
    tryExceptHandler(
        pool.burnLimitOrder,
        "Position doesn't exist",
        TEST_TOKENS[0],
        accounts[0],
        closeIniTickRDown,
        0,
    )
    tryExceptHandler(
        pool.burnLimitOrder,
        "Position doesn't exist",
        TEST_TOKENS[1],
        accounts[0],
        closeIniTickRUp,
        0,
    )

    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], closeIniTickRDown, 1)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], closeIniTickRUp, 1)

    # Positions "inverted" compared to the normal test because the position with TEST_TOKENS[0]
    # will accrue fees in token1 (swaps oneForZero) while TEST_TOKENS[1] in token0 (swaps zeroForOne)
    positionLimit1 = pool.limitOrders[
        getLimitPositionKey(accounts[0], closeIniTickRDown, True)
    ]

    positionLimit0 = pool.limitOrders[
        getLimitPositionKey(accounts[0], closeIniTickRUp, False)
    ]
    assert positionLimit0.liquidity == 1
    assert positionLimit1.liquidity == 1

    # Orig value: 102084710076281216349243831104605583
    assert (
        positionLimit0.feeGrowthInsideLastX128 == 102084710076281539039012382229530463
    )
    # Orig value: 10208471007628121634924383110460558
    assert positionLimit1.feeGrowthInsideLastX128 == 10208471007628153903901238222953046
    # No position burnt and no fees accured
    assert positionLimit0.tokensOwed0 == 0, "tokens owed 0 before"
    assert positionLimit0.tokensOwed1 == 0, "tokens owed 1 before"
    assert positionLimit1.tokensOwed0 == 0, "tokens owed 0 before"
    assert positionLimit1.tokensOwed1 == 0, "tokens owed 1 before"

    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], closeIniTickRDown, 1)
    pool.burnLimitOrder(TEST_TOKENS[1], accounts[0], closeIniTickRUp, 1)

    positionLimit1 = pool.limitOrders[
        getLimitPositionKey(accounts[0], closeIniTickRDown, True)
    ]

    positionLimit0 = pool.limitOrders[
        getLimitPositionKey(accounts[0], closeIniTickRUp, False)
    ]

    assert positionLimit0.liquidity == 0
    assert positionLimit1.liquidity == 0
    assert (
        positionLimit0.feeGrowthInsideLastX128 == 102084710076281539039012382229530463
    )
    assert positionLimit1.feeGrowthInsideLastX128 == 10208471007628153903901238222953046
    # 1 token from the positions burnt and no fees accured
    assert positionLimit0.tokensOwed0 == 0, "tokens owed 0 before"
    assert positionLimit0.tokensOwed1 == 1, "tokens owed 1 before"
    assert positionLimit1.tokensOwed0 == 1, "tokens owed 0 before"
    assert positionLimit1.tokensOwed1 == 0, "tokens owed 1 before"


# Burn

## the combined amount of liquidity that the pool is initialized with (including the 1 minimum liquidity that is burned)
initializeLiquidityAmount = expandTo18Decimals(2)


def initializeAtZeroTick(pool, accounts):
    pool.initialize(encodePriceSqrt(1, 1))
    tickSpacing = pool.tickSpacing
    # [min, max] = [getMinTickLO(tickSpacing), getMaxTickLO(tickSpacing)]

    # Using this instead because the prices at min and max Tick for LO are really off (zero or infinite). Setting them
    # closest to current tick so they are used as LO fallbacks.
    tickLow = pool.slot0.tick
    tickHigh = pool.slot0.tick + tickSpacing

    # NOTE: For token0 (swap1for0) we can take a LO at the current tick, but not in the other direction.
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], tickLow, initializeLiquidityAmount)
    pool.mintLimitOrder(
        TEST_TOKENS[1],
        accounts[0],
        tickHigh,
        initializeLiquidityAmount,
    )


@pytest.fixture
def mediumPoolInitializedAtZero(createPoolMedium, accounts):
    pool, _, _, _, _ = createPoolMedium
    initializeAtZeroTick(pool, accounts)

    # pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], pool.slot0.tick, 3161)
    # pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], pool.slot0.tick, 3161)

    return createPoolMedium


def checkLimitTickIsClear(tickmap, tick):
    assert tickmap.__contains__(tick) == False


def checkLimitTickIsNotClear(tickmap, tick):
    # Make check explicit
    assert tickmap.__contains__(tick)
    assert tickmap[tick].liquidityGross != 0


def test_notClearPosition_ifNoMoreLiquidity(accounts, mediumPoolInitializedAtZero):
    pool, _, _, _, _ = mediumPoolInitializedAtZero
    print("does not clear the position fee growth snapshot if no more liquidity")
    iniTick = pool.slot0.tick
    ## some activity that would make the ticks non-zero
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[1], iniTick, expandTo18Decimals(1))
    pool.mintLimitOrder(
        TEST_TOKENS[1], accounts[1], iniTick + pool.tickSpacing, expandTo18Decimals(1)
    )

    swapExact0For1(pool, expandTo18Decimals(1), accounts[0], None)
    swapExact1For0(pool, expandTo18Decimals(1), accounts[0], None)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[1], iniTick, expandTo18Decimals(1))
    pool.burnLimitOrder(
        TEST_TOKENS[1], accounts[1], iniTick + pool.tickSpacing, expandTo18Decimals(1)
    )

    positionLimitInfo0 = pool.limitOrders[
        getLimitPositionKey(accounts[1], iniTick, True)
    ]
    positionLimitInfo1 = pool.limitOrders[
        getLimitPositionKey(accounts[1], iniTick + pool.tickSpacing, False)
    ]
    assert positionLimitInfo0.liquidity == 0
    assert positionLimitInfo0.tokensOwed0 != 0
    assert positionLimitInfo0.tokensOwed1 != 0
    assert (
        positionLimitInfo0.feeGrowthInsideLastX128
        == 340282366920938463463374607431768211
    )

    assert positionLimitInfo1.liquidity == 0
    assert positionLimitInfo1.tokensOwed0 != 0
    assert positionLimitInfo1.tokensOwed1 != 0
    assert (
        positionLimitInfo1.feeGrowthInsideLastX128
        == 340282366920938463463374607431768211
    )


# NOTE: These three tests don't make a lot of sense in limit orders, since there is not a low and high tick for each
# position. So we are just testing that the correct positions get burn automatically when swapped


def test_clearsTick_ifLastPosition(accounts, mediumPoolInitializedAtZero):
    print("clears the tick if its the last position using it")
    pool, _, _, _, tickSpacing = mediumPoolInitializedAtZero
    ## some activity that would make the ticks non-zero - make it different than mediumPoolInitializedAtZero positions
    tickLow = pool.slot0.tick + tickSpacing * 5
    tickHigh = pool.slot0.tick + tickSpacing * 10
    # Check that ticks are cleared before minting
    checkLimitTickIsClear(pool.ticksLimitTokens0, tickLow)
    checkLimitTickIsClear(pool.ticksLimitTokens1, tickHigh)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], tickLow, expandTo18Decimals(1))
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], tickHigh, expandTo18Decimals(1))
    swapExact0For1(pool, expandTo18Decimals(1), accounts[0], None)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], tickLow, expandTo18Decimals(1))
    assertLimitPositionIsBurnt(
        pool.limitOrders, accounts[0], tickLow, TEST_TOKENS[1] == pool.token0
    )
    checkLimitTickIsClear(pool.ticksLimitTokens0, tickLow)
    checkLimitTickIsClear(pool.ticksLimitTokens1, tickHigh)


def test_clearOnlyUsed(accounts, mediumPoolInitializedAtZero):
    print("clears only the lower tick if upper is still used")
    pool, _, _, _, tickSpacing = mediumPoolInitializedAtZero
    tickLow = pool.slot0.tick - tickSpacing * 10
    tickHigh = pool.slot0.tick + tickSpacing * 10
    ## some activity that would make the ticks non-zero
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], tickLow, 1)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], tickHigh, 1)
    swapExact0For1(pool, expandTo18Decimals(1), accounts[0], None)
    checkLimitTickIsClear(pool.ticksLimitTokens0, tickHigh)
    checkLimitTickIsNotClear(pool.ticksLimitTokens0, tickLow)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], tickLow, 1)
    checkLimitTickIsClear(pool.ticksLimitTokens0, tickLow)


# Miscellaneous mint tests
@pytest.fixture
def lowPoolInitializedAtZero(createPoolLow, accounts):
    pool, _, _, _, _ = createPoolLow
    initializeAtZeroTick(pool, accounts)
    return createPoolLow


def test_mintGood_currentPrice(lowPoolInitializedAtZero, accounts):
    print("mint to the right of the current price")
    pool, _, _, _, tickSpacing = lowPoolInitializedAtZero
    liquidityDelta = 1000
    lowerTick = tickSpacing
    upperTick = tickSpacing * 2
    liquidityBefore = pool.liquidity
    b0 = pool.balances[TEST_TOKENS[0]]
    b1 = pool.balances[TEST_TOKENS[1]]

    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], lowerTick, liquidityDelta)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], upperTick, liquidityDelta)

    liquidityAfter = pool.liquidity
    assert liquidityAfter >= liquidityBefore

    assert pool.balances[TEST_TOKENS[0]] - b0 == liquidityDelta
    assert pool.balances[TEST_TOKENS[1]] - b1 == liquidityDelta


def test_mintBad_currentPrice(lowPoolInitializedAtZero, accounts):
    print("mint to the right of the current price")
    pool, _, _, _, tickSpacing = lowPoolInitializedAtZero
    liquidityDelta = 1000
    lowerTick = -tickSpacing * 2
    upperTick = -tickSpacing
    liquidityBefore = pool.liquidity
    b0 = pool.balances[TEST_TOKENS[0]]
    b1 = pool.balances[TEST_TOKENS[1]]

    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], lowerTick, liquidityDelta)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], upperTick, liquidityDelta)

    liquidityAfter = pool.liquidity
    assert liquidityAfter >= liquidityBefore

    assert pool.balances[TEST_TOKENS[0]] - b0 == liquidityDelta
    assert pool.balances[TEST_TOKENS[1]] - b1 == liquidityDelta


def test_mint_withinCurrentPrice(lowPoolInitializedAtZero, accounts):
    print("mint within the current price")
    pool, _, _, _, tickSpacing = lowPoolInitializedAtZero
    liquidityDelta = 1000
    lowerTick = -tickSpacing
    upperTick = tickSpacing
    liquidityBefore = pool.liquidity
    b0 = pool.balances[TEST_TOKENS[0]]
    b1 = pool.balances[TEST_TOKENS[1]]

    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], lowerTick, liquidityDelta)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], upperTick, liquidityDelta)

    liquidityAfter = pool.liquidity
    assert liquidityAfter >= liquidityBefore

    assert pool.balances[TEST_TOKENS[0]] - b0 == liquidityDelta
    assert pool.balances[TEST_TOKENS[1]] - b1 == liquidityDelta


def test_cannotRemove_moreThanPosition(lowPoolInitializedAtZero, accounts):
    print("cannot remove more than the entire position")
    pool, _, _, _, tickSpacing = lowPoolInitializedAtZero
    lowerTick = -tickSpacing * 2
    upperTick = tickSpacing * 2

    pool.mintLimitOrder(
        TEST_TOKENS[0], accounts[0], lowerTick, expandTo18Decimals(1000)
    )
    pool.mintLimitOrder(
        TEST_TOKENS[1], accounts[0], upperTick, expandTo18Decimals(1000)
    )

    tryExceptHandler(
        pool.burnLimitOrder,
        "LS",
        TEST_TOKENS[0],
        accounts[0],
        lowerTick,
        expandTo18Decimals(1001),
    )
    tryExceptHandler(
        pool.burnLimitOrder,
        "LS",
        TEST_TOKENS[1],
        accounts[0],
        upperTick,
        expandTo18Decimals(1001),
    )


def test_collectFee_currentPrice(lowPoolInitializedAtZero, accounts, ledger):
    print("collect fees within the current price after swap")
    pool, _, _, _, tickSpacing = lowPoolInitializedAtZero
    liquidityDelta = expandTo18Decimals(100)
    lowerTick = -tickSpacing * 100
    upperTick = tickSpacing * 100

    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], lowerTick, liquidityDelta)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], upperTick, liquidityDelta)

    beforeTick0 = copy.deepcopy(pool.ticksLimitTokens0[lowerTick])
    beforeTick1 = copy.deepcopy(pool.ticksLimitTokens1[upperTick])

    amount0In = expandTo18Decimals(1)

    swapExact0For1(pool, amount0In, accounts[0], None)

    afterTick0 = pool.ticksLimitTokens0[lowerTick]
    afterTick1 = pool.ticksLimitTokens1[upperTick]

    assert afterTick0 == beforeTick0
    assert afterTick1 != beforeTick1
    assert afterTick1.liquidityLeft < beforeTick1.liquidityLeft
    assert afterTick1.liquidityGross == beforeTick1.liquidityGross
    assert (
        afterTick1.amountPercSwappedInsideX128 > beforeTick1.amountPercSwappedInsideX128
    )
    assert afterTick1.feeGrowthInsideX128 > beforeTick1.feeGrowthInsideX128

    token0BalanceBeforePool = pool.balances[TEST_TOKENS[0]]
    token1BalanceBeforePool = pool.balances[TEST_TOKENS[1]]
    token0BalanceBeforeWallet = ledger.balanceOf(accounts[0], TEST_TOKENS[0])
    token1BalanceBeforeWallet = ledger.balanceOf(accounts[0], TEST_TOKENS[1])

    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], lowerTick, 0)
    pool.burnLimitOrder(TEST_TOKENS[1], accounts[0], upperTick, 0)
    pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[0], lowerTick, MAX_UINT128, MAX_UINT128
    )
    pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[1], upperTick, MAX_UINT128, MAX_UINT128
    )

    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], lowerTick, 0)
    pool.burnLimitOrder(TEST_TOKENS[1], accounts[0], upperTick, 0)

    (_, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[0], lowerTick, MAX_UINT128, MAX_UINT128
    )
    assert amount0 == 0
    assert amount1 == 0

    (_, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[1], upperTick, MAX_UINT128, MAX_UINT128
    )

    assert amount0 == 0
    assert amount1 == 0

    token0BalanceAfterPool = pool.balances[TEST_TOKENS[0]]
    token1BalanceAfterPool = pool.balances[TEST_TOKENS[1]]
    token0BalanceAfterWallet = ledger.balanceOf(accounts[0], TEST_TOKENS[0])
    token1BalanceAfterWallet = ledger.balanceOf(accounts[0], TEST_TOKENS[1])

    assert token0BalanceAfterWallet > token0BalanceBeforeWallet
    assert token1BalanceAfterWallet == token1BalanceBeforeWallet
    assert token0BalanceAfterPool < token0BalanceBeforePool
    assert token1BalanceAfterPool == token1BalanceBeforePool


# pre-initialize at medium fee
def test_preInitialized_mediumFee(createPoolMedium):
    print("pre-initialized at medium fee")
    pool, _, _, _, _ = createPoolMedium
    assert pool.liquidity == 0


# post-initialize at medium fee
def test_initialLiquidity(mediumPoolInitializedAtZero):
    print("returns initial liquidity")
    pool, _, _, _, _ = mediumPoolInitializedAtZero
    assert pool.liquidity == 0
    tickLow = pool.slot0.tick
    tickHigh = pool.slot0.tick + pool.tickSpacing
    assert (
        pool.ticksLimitTokens0[tickLow].liquidityLeft
        + pool.ticksLimitTokens1[tickHigh].liquidityLeft
        == expandTo18Decimals(2) * 2
    )


def test_supplyInRange(mediumPoolInitializedAtZero, accounts):
    print("returns in supply in range")
    pool, _, _, _, tickSpacing = mediumPoolInitializedAtZero
    pool.mintLimitOrder(
        TEST_TOKENS[0], accounts[0], -tickSpacing, expandTo18Decimals(3)
    )
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], tickSpacing, expandTo18Decimals(3))
    assert (
        pool.ticksLimitTokens0[0].liquidityLeft
        + pool.ticksLimitTokens0[-tickSpacing].liquidityLeft
        + pool.ticksLimitTokens1[tickSpacing].liquidityLeft
        == expandTo18Decimals(5) * 2
    )


# These tests don't make sense for LO

# def test_excludeSupply_tickAboveCurrentTick(mediumPoolInitializedAtZero, accounts):
#     print("excludes supply at tick above current tick")
#     pool, _, _, _, tickSpacing = mediumPoolInitializedAtZero
#     pool.mintLimitOrder(TEST_TOKENS[0],accounts[0], tickSpacing, tickSpacing * 2, expandTo18Decimals(3))
#     assert pool.liquidity == expandTo18Decimals(2)


# def test_excludeSupply_tickBelowCurrentTick(mediumPoolInitializedAtZero, accounts):
#     print("excludes supply at tick below current tick")
#     pool, _, _, _, tickSpacing = mediumPoolInitializedAtZero
#     pool.mintLimitOrder(TEST_TOKENS[0],accounts[0], -tickSpacing * 2, -tickSpacing, expandTo18Decimals(3))
#     assert pool.liquidity == expandTo18Decimals(2)


# def test_updatesWhenExitingRange(mediumPoolInitializedAtZero, accounts):
#     print("updates correctly when exiting range")
#     pool, _, _, _, tickSpacing = mediumPoolInitializedAtZero

#     kBefore = pool.liquidity
#     assert kBefore == expandTo18Decimals(2)

#     ## add liquidity at and above current tick
#     liquidityDelta = expandTo18Decimals(1)
#     lowerTick = 0
#     upperTick = tickSpacing
#     pool.mintLimitOrder(TEST_TOKENS[0],accounts[0], lowerTick, upperTick, liquidityDelta)

#     ## ensure virtual supply has increased appropriately
#     kAfter = pool.liquidity
#     assert kAfter == expandTo18Decimals(3)

#     ## swap toward the left (just enough for the tick transition function to trigger)
#     swapExact0For1(pool, 1, accounts[0], None)
#     assert pool.slot0.tick == -1

#     kAfterSwap = pool.liquidity
#     assert kAfterSwap == expandTo18Decimals(2)


# def test_updatesWhenEnteringRange(mediumPoolInitializedAtZero, accounts):
#     print("updates correctly when entering range")
#     pool, _, _, _, tickSpacing = mediumPoolInitializedAtZero

#     kBefore = pool.liquidity
#     assert kBefore == expandTo18Decimals(2)

#     ## add liquidity at and below current tick
#     liquidityDelta = expandTo18Decimals(1)
#     lowerTick = -tickSpacing
#     upperTick = 0
#     pool.mintLimitOrder(TEST_TOKENS[0],accounts[0], lowerTick, upperTick, liquidityDelta)

#     ## ensure virtual supply has increased appropriately
#     kAfter = pool.liquidity
#     assert kAfter == kBefore
#     ## swap toward the right (just enough for the tick transition function to trigger)
#     swapExact0For1(pool, 1, accounts[0], None)
#     assert pool.slot0.tick == -1

#     kAfterSwap = pool.liquidity
#     assert kAfterSwap == expandTo18Decimals(3)


# Limit orders (still uniswap tests)


def test_limitSelling0For1_atTick0Thru1(mediumPoolInitializedAtZero, accounts, ledger):
    print("limit selling 0 for 1 at tick 0 thru 1")
    pool, _, _, _, _ = mediumPoolInitializedAtZero

    # Value to emulate minted liquidity in Uniswap
    liquidityToMint = 5981737760509663
    amount0 = pool.mintLimitOrder(
        TEST_TOKENS[0], accounts[0], -pool.tickSpacing, liquidityToMint
    )
    assert amount0 == liquidityToMint

    iniBalance0LP = ledger.balanceOf(accounts[0], TEST_TOKENS[0])
    iniBalance1LP = ledger.balanceOf(accounts[0], TEST_TOKENS[1])

    ## somebody takes the limit order
    swapExact1For0(pool, expandTo18Decimals(2), accounts[1], None)

    # We have crossed the position is already burnt
    finalBalance0LP = ledger.balanceOf(accounts[0], TEST_TOKENS[0])
    finalBalance1LP = ledger.balanceOf(accounts[0], TEST_TOKENS[1])

    assert finalBalance0LP == iniBalance0LP

    # Original value: 18107525382602. Slightly different because the amount swapped in the position/tick will be
    # slightly different (tick will be crossed with slightly different amounts)
    feesAccrued = 17891544354686
    positionSwapped = mulDiv(
        abs(liquidityToMint), TickMath.getPriceAtTick(-pool.tickSpacing), 2**96
    )

    assert finalBalance1LP == iniBalance1LP + positionSwapped + feesAccrued


# # Fee is ON
def test_limitSelling0For1_atTick0Thru1_feesOn(
    mediumPoolInitializedAtZero, accounts, ledger
):
    print("limit selling 0 for 1 at tick 0 thru 1 - fees on")
    pool, _, _, _, _ = mediumPoolInitializedAtZero
    pool.setFeeProtocol(6, 6)

    # Value to emulate minted liquidity in Uniswap
    liquidityToMint = 5981737760509663
    amount0 = pool.mintLimitOrder(
        TEST_TOKENS[0], accounts[0], -pool.tickSpacing, liquidityToMint
    )
    assert amount0 == liquidityToMint

    iniBalance0LP = ledger.balanceOf(accounts[0], TEST_TOKENS[0])
    iniBalance1LP = ledger.balanceOf(accounts[0], TEST_TOKENS[1])

    ## somebody takes the limit order
    swapExact1For0(pool, expandTo18Decimals(2), accounts[1], None)

    # We have crossed the position is already burnt
    finalBalance0LP = ledger.balanceOf(accounts[0], TEST_TOKENS[0])
    finalBalance1LP = ledger.balanceOf(accounts[0], TEST_TOKENS[1])

    assert finalBalance0LP == iniBalance0LP

    # Original value: 15089604485501. Slightly different because the amount swapped in the position/tick will be
    # slightly different (tick will be crossed with slightly different amounts)
    ## roughly 0.25% despite other liquidity - same percentatge difference as in Uniswap
    feesAccrued = 14909620295572
    positionSwapped = mulDiv(
        abs(liquidityToMint), TickMath.getPriceAtTick(-pool.tickSpacing), 2**96
    )

    assert finalBalance1LP == iniBalance1LP + positionSwapped + feesAccrued


# # This doesn't make sense for LO.

# # def test_limitSelling0For1_atTick0ThruMinus1_feesOn(
# #     mediumPoolInitializedAtZero, accounts
# # ):
# #     print("limit selling 0 for 1 at tick 0 thru -1 - fees on")
# #     pool, _, _, _, _ = mediumPoolInitializedAtZero
# #     pool.setFeeProtocol(6, 6)

# #     (amount0, amount1) = pool.mintLimitOrder(TEST_TOKENS[0],accounts[0], -120, 0, expandTo18Decimals(1))
# #     assert amount0 == 0
# #     assert amount1 == 5981737760509663

# #     ## somebody takes the limit order
# #     swapExact0For1(pool, expandTo18Decimals(2), accounts[0], None)

# #     (recipient, tickLower, tickUpper, amount, amount0, amount1) = pool.burnLimitOrder(TEST_TOKENS[0],
# #         accounts[0], -120, 0, expandTo18Decimals(1)
# #     )
# #     assert recipient == accounts[0]
# #     assert tickLower == -120
# #     assert tickUpper == 0
# #     assert amount == expandTo18Decimals(1)
# #     assert amount0 == 6017734268818165
# #     assert amount1 == 0

# #     (recipient, _, _, amount0, amount1) = pool.collect(
# #         accounts[0], -120, 0, MAX_UINT128, MAX_UINT128
# #     )
# #     assert recipient == accounts[0]
# #     assert (
# #         amount0 == 6017734268818165 + 15089604485501
# #     )  ## roughly 0.25% despite other liquidity
# #     assert amount1 == 0

# #     assert pool.slot0.tick <= -120


# ## Collect
# def test_multipleLPs(initializedLowPoolCollect, accounts):
#     print("works with multiple LPs")
#     pool, _, _, _, tickSpacing = initializedLowPoolCollect

#     tick = tickSpacing

#     pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], tick, expandTo18Decimals(1))
#     pool.mintLimitOrder(TEST_TOKENS[1], accounts[1], tick, expandTo18Decimals(2))

#     swapExact0For1(pool, expandTo18Decimals(1), accounts[0], None)

#     ## poke limitOrders
#     pool.burnLimitOrder(TEST_TOKENS[1], accounts[0], tick, 0)
#     pool.burnLimitOrder(TEST_TOKENS[1], accounts[1], tick, 0)

#     position0 = pool.limitOrders[getLimitPositionKey(accounts[0], tick, False)]
#     position1 = pool.limitOrders[getLimitPositionKey(accounts[1], tick, False)]

#     assert position0.tokensOwed0 == 166666666666666
#     assert position1.tokensOwed0 == 333333333333333


## Works accross large increases

## type(uint128).max * 2**128 / 1e18
## https://www.wolframalpha.com/input/?i=%282**128+-+1%29+*+2**128+%2F+1e18
magicNumber = 115792089237316195423570985008687907852929702298719625575994


def test_justBeforeCapBinds(initializedLowPoolCollect, accounts):
    print("works just before the cap binds")
    pool, _, _, _, _ = initializedLowPoolCollect
    iniTick = pool.slot0.tick
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], iniTick, expandTo18Decimals(1))
    pool.ticksLimitTokens0[iniTick].feeGrowthInsideX128 = magicNumber
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], iniTick, 0)
    positionInfo = pool.limitOrders[getLimitPositionKey(accounts[0], iniTick, True)]
    # Reversed tokens since a position0 will accrue tokens1 fees
    assert positionInfo.tokensOwed1 == MAX_UINT128 - 1
    assert positionInfo.tokensOwed0 == 0


def test_justAfterCapBinds(initializedLowPoolCollect, accounts):
    print("works just after the cap binds")
    pool, _, _, _, _ = initializedLowPoolCollect
    iniTick = pool.slot0.tick
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], iniTick, expandTo18Decimals(1))

    pool.ticksLimitTokens0[iniTick].feeGrowthInsideX128 = magicNumber + 1
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], iniTick, 0)

    positionInfo = pool.limitOrders[getPositionKey(accounts[0], iniTick, True)]

    # Reversed tokens since a position0 will accrue tokens1 fees
    assert positionInfo.tokensOwed1 == MAX_UINT128
    assert positionInfo.tokensOwed0 == 0


# Causes overflow on the position.update() for tokensOwed0. In Uniswap the overflow is
# acceptable because it is expected for the LP to collect the tokens before it happens.
def test_afterCapBinds(initializedLowPoolCollect, accounts):
    print("works after the cap binds")
    pool, _, _, _, _ = initializedLowPoolCollect
    iniTick = pool.slot0.tick
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], iniTick, expandTo18Decimals(1))

    pool.ticksLimitTokens0[iniTick].feeGrowthInsideX128 = MAX_UINT256

    # Overflown tokensOwed0 - added code to Position.py to handle this
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], iniTick, 0)

    positionInfo = pool.limitOrders[getPositionKey(accounts[0], iniTick, True)]

    assert positionInfo.tokensOwed1 == MAX_UINT128
    assert positionInfo.tokensOwed0 == 0


# Works across overflow boundaries
@pytest.fixture
def initializedLowPoolCollectGrowthFees(initializedLowPoolCollect, accounts):
    pool, _, _, _, _ = initializedLowPoolCollect
    iniTick = pool.slot0.tick

    # Need to mint LO first before being able to set a tick's feeGrowthInsideX128
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], iniTick, expandTo18Decimals(10))
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], iniTick, expandTo18Decimals(10))

    pool.ticksLimitTokens0[iniTick].feeGrowthInsideX128 = MAX_UINT256
    pool.ticksLimitTokens1[iniTick].feeGrowthInsideX128 = MAX_UINT256
    return initializedLowPoolCollect


def test_token0(initializedLowPoolCollectGrowthFees, accounts):
    print("token0")
    pool, _, _, _, _ = initializedLowPoolCollectGrowthFees
    iniTick = pool.slot0.tick

    # Change the direction of the swap to test token0 position
    swapExact1For0(pool, expandTo18Decimals(1), accounts[0], None)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], iniTick, 0)
    (_, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[0], iniTick, MAX_UINT128, MAX_UINT128
    )
    # Reversed tokens since a position0 will accrue tokens1 fees
    assert amount1 == 499999999999999
    assert amount0 == 0


def test_token1(initializedLowPoolCollectGrowthFees, accounts):
    print("token1")
    pool, _, _, _, _ = initializedLowPoolCollectGrowthFees

    iniTick = pool.slot0.tick
    # Move tick so we can use the token1 LO set on tick0
    pool.slot0.tick = pool.slot0.tick - pool.tickSpacing

    swapExact0For1(pool, expandTo18Decimals(1), accounts[0], None)
    pool.burnLimitOrder(TEST_TOKENS[1], accounts[0], iniTick, 0)
    (_, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[1], iniTick, MAX_UINT128, MAX_UINT128
    )

    # Reversed tokens since a position1 will accrue tokens0 fees
    assert amount1 == 0
    assert amount0 == 499999999999999


def test_token0_and_token1(initializedLowPoolCollectGrowthFees, accounts):
    print("token0 and token1")
    pool, _, _, _, _ = initializedLowPoolCollectGrowthFees
    iniTick = pool.slot0.tick

    swapExact1For0(pool, expandTo18Decimals(1), accounts[0], None)

    pool.slot0.tick = pool.slot0.tick - pool.tickSpacing

    swapExact0For1(pool, expandTo18Decimals(1), accounts[0], None)
    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], iniTick, 0)
    pool.burnLimitOrder(TEST_TOKENS[1], accounts[0], iniTick, 0)

    (_, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[0], iniTick, MAX_UINT128, MAX_UINT128
    )
    assert amount1 == 499999999999999
    assert amount0 == 0

    (_, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[1], iniTick, MAX_UINT128, MAX_UINT128
    )
    assert amount1 == 0
    assert amount0 == 499999999999999


# Fee Protocol
liquidityAmount = expandTo18Decimals(1000)


@pytest.fixture
def initializedLowPoolCollectFees(initializedLowPoolCollect, accounts):
    pool, _, _, _, _ = initializedLowPoolCollect

    iniTick = pool.slot0.tick
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], iniTick, liquidityAmount)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], iniTick, liquidityAmount)

    return initializedLowPoolCollect


def test_initiallyZero(initializedLowPoolCollectFees):
    print("is initially set to 0")
    pool, _, _, _, _ = initializedLowPoolCollectFees

    assert pool.slot0.feeProtocol == 0


def test_changeProtocolFee(initializedLowPoolCollectFees):
    print("can be changed")
    pool, _, _, _, _ = initializedLowPoolCollectFees

    pool.setFeeProtocol(6, 6)
    assert pool.slot0.feeProtocol == 102


def test_cannotOutOfBounds(initializedLowPoolCollectFees):
    pool, _, _, _, _ = initializedLowPoolCollectFees
    tryExceptHandler(pool.setFeeProtocol, "", 3, 3)
    tryExceptHandler(pool.setFeeProtocol, "", 11, 11)


def swapAndGetFeesOwed(createPoolParams, amount, zeroForOne, poke, account, tick):
    pool, _, _, _, _ = createPoolParams

    if zeroForOne:
        # Move tick so we can use the token1 LO set on tick0
        pool.slot0.tick = tick - pool.tickSpacing
        swapExact0For1(pool, amount, account, None)
        token = TEST_TOKENS[1]

    else:
        # In case of multiple swaps, set the tick back to the tick where the LO is set
        pool.slot0.tick = tick
        swapExact1For0(pool, amount, account, None)
        token = TEST_TOKENS[0]

    if poke:
        pool.burnLimitOrder(token, account, tick, 0)

    # Copy pool instance to check that the accrued fees are correct but allowing to accumulate
    if zeroForOne:
        (_, _, fees0, fees1) = copy.deepcopy(pool).collectLimitOrder(
            account, token, tick, MAX_UINT128, MAX_UINT128
        )
    else:
        (_, _, fees0, fees1) = copy.deepcopy(pool).collectLimitOrder(
            account, token, tick, MAX_UINT128, MAX_UINT128
        )

    assert fees0 >= 0, "fees owed in token0 are greater than 0"
    assert fees1 >= 0, "fees owed in token1 are greater than 0"

    return (fees0, fees1)


def test_positionOwner_fullFees_feeProtocolOff(initializedLowPoolCollectFees, accounts):
    print("position owner gets full fees when protocol fee is off")
    pool, _, _, _, _ = initializedLowPoolCollectFees

    (token0Fees, token1Fees) = swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        True,
        True,
        accounts[0],
        pool.slot0.tick,
    )
    ## 6 bips * 1e18
    assert token0Fees == 499999999999999
    assert token1Fees == 0


def test_swapFeesAccomulate_zeroForOne(initializedLowPoolCollectFees, accounts):
    print("swap fees accumulate as expected (0 for 1)")
    pool, _, _, _, _ = initializedLowPoolCollectFees

    iniTick = pool.slot0.tick

    (token0Fees, token1Fees) = swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        True,
        True,
        accounts[0],
        iniTick,
    )
    assert token0Fees == 499999999999999
    assert token1Fees == 0

    # TODO: Debugging - why fees are higher swapping twice than doing one bigger swap?
    (token0Fees, token1Fees) = swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        True,
        True,
        accounts[0],
        iniTick,
    )
    assert token0Fees == 999999999999998
    assert token1Fees == 0

    (token0Fees, token1Fees) = swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        True,
        True,
        accounts[0],
        iniTick,
    )
    assert token0Fees == 1499999999999997
    assert token1Fees == 0


def test_swapFeesAccomulate_zeroForOne_together0(
    initializedLowPoolCollectFees, accounts
):
    print("swap fees accumulate as expected (0 for 1)")
    pool, _, _, _, _ = initializedLowPoolCollectFees

    iniTick = pool.slot0.tick

    (token0Fees, token1Fees) = swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(2),
        True,
        True,
        accounts[0],
        iniTick,
    )
    assert token0Fees == 999999999999999
    assert token1Fees == 0


# check that swapping 1e18 three times adds to almost the same exact fees as swapping 3e18 once
def test_swapFeesAccomulate_zeroForOne_together1(
    initializedLowPoolCollectFees, accounts
):
    print("swap fees accumulate as expected (0 for 1)")
    pool, _, _, _, _ = initializedLowPoolCollectFees

    iniTick = pool.slot0.tick

    (token0Fees, token1Fees) = swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(3),
        True,
        True,
        accounts[0],
        iniTick,
    )
    assert token0Fees == 1499999999999999
    assert token1Fees == 0


def test_swapFeesAccomulate_OneForZero(initializedLowPoolCollectFees, accounts):
    print("swap fees accumulate as expected (1 for 0)")
    pool, _, _, _, _ = initializedLowPoolCollectFees
    iniTick = pool.slot0.tick

    (token0Fees, token1Fees) = swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        False,
        True,
        accounts[0],
        iniTick,
    )

    assert token0Fees == 0
    assert token1Fees == 499999999999999

    (token0Fees, token1Fees) = swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        False,
        True,
        accounts[0],
        iniTick,
    )
    assert token0Fees == 0
    assert token1Fees == 999999999999998

    (token0Fees, token1Fees) = swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        False,
        True,
        accounts[0],
        iniTick,
    )
    assert token0Fees == 0
    assert token1Fees == 1499999999999997


# check that swapping 1e18 multiple times adds to almost the same exact fees as swapping once
def test_swapFeesAccomulate_OneForZero(initializedLowPoolCollectFees, accounts):
    print("swap fees accumulate as expected (1 for 0)")
    pool, _, _, _, _ = initializedLowPoolCollectFees
    iniTick = pool.slot0.tick

    (token0Fees, token1Fees) = swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(2),
        False,
        True,
        accounts[0],
        iniTick,
    )

    assert token0Fees == 0
    assert token1Fees == 999999999999999


def test_swapFeesAccomulate_OneForZero(initializedLowPoolCollectFees, accounts):
    print("swap fees accumulate as expected (1 for 0)")
    pool, _, _, _, _ = initializedLowPoolCollectFees
    iniTick = pool.slot0.tick

    (token0Fees, token1Fees) = swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(3),
        False,
        True,
        accounts[0],
        iniTick,
    )

    assert token0Fees == 0
    assert token1Fees == 1499999999999999


def test_partialFees_feeProtocolOn(initializedLowPoolCollectFees, accounts):
    print("position owner gets partial fees when protocol fee is on")
    pool, _, _, _, _ = initializedLowPoolCollectFees
    iniTick = pool.slot0.tick

    pool.setFeeProtocol(6, 6)
    (token0Fees, token1Fees) = swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        True,
        True,
        accounts[0],
        iniTick,
    )
    assert token0Fees == 416666666666666
    assert token1Fees == 0


# Collect protocol


def test_returnsZero_noFees(initializedLowPoolCollectFees, accounts):
    print("returns 0 if no fees")
    pool, _, _, _, _ = initializedLowPoolCollectFees
    pool.setFeeProtocol(6, 6)

    (_, amount0, amount1) = pool.collectProtocol(accounts[0], MAX_UINT128, MAX_UINT128)
    assert amount0 == 0
    assert amount1 == 0


def test_canCollectFees(initializedLowPoolCollectFees, accounts):
    print("can collect fees")
    pool, _, _, _, _ = initializedLowPoolCollectFees
    iniTick = pool.slot0.tick
    pool.setFeeProtocol(6, 6)

    swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        True,
        True,
        accounts[0],
        iniTick,
    )

    (_, amount0, amount1) = pool.collectProtocol(accounts[0], MAX_UINT128, MAX_UINT128)
    assert amount0 == 83333333333332
    assert amount1 == 0


def test_feesDifferToken0Token1(initializedLowPoolCollectFees, accounts):
    print("fees collected can differ between token0 and token1")
    pool, _, _, _, _ = initializedLowPoolCollectFees
    iniTick = pool.slot0.tick

    pool.setFeeProtocol(8, 5)

    swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        True,
        False,
        accounts[0],
        iniTick,
    )

    swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        False,
        False,
        accounts[0],
        iniTick,
    )

    (_, amount0, amount1) = pool.collectProtocol(accounts[0], MAX_UINT128, MAX_UINT128)
    ## more token0 fees because it's 1/5th the swap fees
    assert amount0 == 62499999999999
    ## less token1 fees because it's 1/8th the swap fees
    assert amount1 == 99999999999999


def test_doubleFees(initializedLowPoolCollectFees, accounts):
    print("fees collected by lp after two swaps should be double one swap")

    pool, _, _, _, _ = initializedLowPoolCollectFees
    iniTick = pool.slot0.tick

    swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        True,
        True,
        accounts[0],
        iniTick,
    )

    (token0Fees, token1Fees) = swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        True,
        True,
        accounts[0],
        iniTick,
    )

    ## 6 bips * 2e18
    assert token0Fees == 999999999999998
    assert token1Fees == 0


def test_feesCollected_combination0(initializedLowPoolCollectFees, accounts):
    print(
        "fees collected after two swaps with fee turned on in middle are fees from last swap (not confiscatory)"
    )
    pool, _, _, _, _ = initializedLowPoolCollectFees
    iniTick = pool.slot0.tick

    swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        True,
        False,
        accounts[0],
        iniTick,
    )
    pool.setFeeProtocol(6, 6)
    (token0Fees, token1Fees) = swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        True,
        True,
        accounts[0],
        iniTick,
    )
    assert token0Fees == 916666666666666
    assert token1Fees == 0


def test_feesCollected_combination1(initializedLowPoolCollectFees, accounts):
    print("fees collected by lp after two swaps with intermediate withdrawal")
    pool, minTick, maxTick, _, _ = initializedLowPoolCollectFees
    iniTick = pool.slot0.tick
    pool.setFeeProtocol(6, 6)

    (token0Fees, token1Fees) = swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        True,
        True,
        accounts[0],
        iniTick,
    )
    assert token0Fees == 416666666666666
    assert token1Fees == 0

    pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[0], iniTick, MAX_UINT128, MAX_UINT128
    )
    pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[1], iniTick, MAX_UINT128, MAX_UINT128
    )

    (token0Fees, token1Fees) = swapAndGetFeesOwed(
        initializedLowPoolCollectFees,
        expandTo18Decimals(1),
        True,
        False,
        accounts[0],
        iniTick,
    )
    assert token0Fees == 0
    assert token1Fees == 0

    assert pool.protocolFees.token0 == 166666666666666
    assert pool.protocolFees.token1 == 0

    pool.burnLimitOrder(TEST_TOKENS[0], accounts[0], iniTick, 0)  ## poke to update fees
    pool.burnLimitOrder(TEST_TOKENS[1], accounts[0], iniTick, 0)  ## poke to update fees

    (recipient, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[0], iniTick, MAX_UINT128, MAX_UINT128
    )
    assert (recipient, amount0, amount1) == (accounts[0], 0, 0)

    (recipient, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[1], iniTick, MAX_UINT128, MAX_UINT128
    )
    assert (recipient, amount0, amount1) == (accounts[0], 416666666666666, 0)

    assert pool.protocolFees.token0 == 166666666666666
    assert pool.protocolFees.token1 == 0


@pytest.fixture
def createPoolMedium12TickSpacing(ledger):
    return createPool(FeeAmount.MEDIUM, 12, ledger)


@pytest.fixture
def initializedPoolMedium12TickSpacing(createPoolMedium12TickSpacing):
    pool, _, _, _, _ = createPoolMedium12TickSpacing
    pool.initialize(encodePriceSqrt(1, 1))
    return createPoolMedium12TickSpacing


def test_mint_onlyMultiplesOf12(initializedPoolMedium12TickSpacing, accounts):
    print("mint can only be called for multiples of 12")
    pool, _, _, _, _ = initializedPoolMedium12TickSpacing
    tryExceptHandler(pool.mintLimitOrder, "", TEST_TOKENS[0], accounts[0], -6, 1)
    tryExceptHandler(pool.mintLimitOrder, "", TEST_TOKENS[1], accounts[0], -6, 1)


def test_mint_multiplesOf12(initializedPoolMedium12TickSpacing, accounts):
    print("mint can be called for multiples of 12")
    pool, _, _, _, _ = initializedPoolMedium12TickSpacing
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], 12, 1)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], 24, 1)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], 12, 1)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], 24, 1)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], -144, 1)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], -120, 1)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], -144, 1)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], -120, 1)


def test_swapGaps_oneForZero(initializedPoolMedium12TickSpacing, accounts):
    print("swapping across gaps works in 1 for 0 direction")
    pool, _, _, _, _ = initializedPoolMedium12TickSpacing
    # Change pool current tick so it uses the correct LO orders
    pool.slot0.tick = 150000
    # Liquidity gotten from the amount minted in the Uniswap test
    # liquidityAmount = expandTo18Decimals(1) // 4
    liquidityAmount = 36096898321357
    # Mint two orders and check that it uses the correct one.
    # 120192 being the closest tick to the price that is swapped at Uniswap test
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], 120192, liquidityAmount)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], 121200, liquidityAmount)
    swapExact1For0(pool, expandTo18Decimals(1), accounts[0], None)

    # This order should not have been used
    (recipient, tick, amount, amount0, amount1) = pool.burnLimitOrder(
        TEST_TOKENS[0], accounts[0], 121200, liquidityAmount
    )
    assert recipient == accounts[0]
    assert tick == 121200
    assert amount == liquidityAmount
    assert amount0 == liquidityAmount
    assert amount1 == 0

    (recipient, tick, amount, amount0, amount1) = pool.burnLimitOrder(
        TEST_TOKENS[0], accounts[0], 120192, liquidityAmount
    )
    assert recipient == accounts[0]
    assert tick == 120192
    assert amount == liquidityAmount
    # Slightly different amounts because of price difference
    # Orig value: 30027458295511
    assert amount0 == 30083999478255
    assert amount1 == 996999999999848369

    # Tick should not have changed
    assert pool.slot0.tick == 150000


def test_swapGaps_zeroForOne(initializedPoolMedium12TickSpacing, accounts):
    print("swapping across gaps works in 0 for 1 direction")
    pool, _, _, _, _ = initializedPoolMedium12TickSpacing
    # Change pool current tick so it uses the correct LO orders
    pool.slot0.tick = -150000
    # Liquidity gotten from the amount minted in the Uniswap test
    # liquidityAmount = expandTo18Decimals(1) // 4
    liquidityAmount = 36096898321357
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], -121200, liquidityAmount)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], -120192, liquidityAmount)
    swapExact0For1(pool, expandTo18Decimals(1), accounts[0], None)

    # This order should not have been used
    (recipient, tick, amount, amount0, amount1) = pool.burnLimitOrder(
        TEST_TOKENS[1], accounts[0], -121200, liquidityAmount
    )
    assert recipient == accounts[0]
    assert tick == -121200
    assert amount == liquidityAmount
    assert amount0 == 0
    assert amount1 == liquidityAmount

    (recipient, tick, amount, amount0, amount1) = pool.burnLimitOrder(
        TEST_TOKENS[1], accounts[0], -120192, liquidityAmount
    )
    assert recipient == accounts[0]
    assert tick == -120192
    # Slightly different amounts because of price difference
    assert amount == liquidityAmount
    # Slightly different amounts because of price difference
    # Orig value: 30027458295511
    assert amount0 == 996999999999848369
    assert amount1 == 30083999478255

    # Tick should not have changed
    assert pool.slot0.tick == -150000


# Doesn't make sense with limit orders

# ## https://github.com/Uniswap/uniswap-v3-core/issues/214
# def test_noTickTransitionTwice(accounts):
#     print(
#         "tick transition cannot run twice if zero for one swap ends at fractional price just below tick"
#     )
#     pool, _, _, _, _ = createPool(FeeAmount.MEDIUM, 1, ledger)

#     p0 = TickMath.getSqrtRatioAtTick(-24081) + 1
#     ## initialize at a price of ~0.3 token1/token0
#     ## meaning if you swap in 2 token0, you should end up getting 0 token1
#     pool.initialize(p0)
#     assert pool.liquidity == 0, "current pool liquidity is 1"
#     assert pool.slot0.tick == -24081, "pool tick is -24081"

#     ## add a bunch of liquidity around current price
#     liquidity = expandTo18Decimals(1000)
#     pool.mintLimitOrder(TEST_TOKENS[0],accounts[0], -24082, -24080, liquidity)
#     assert pool.liquidity == liquidity, "current pool liquidity is now liquidity + 1"

#     pool.mintLimitOrder(TEST_TOKENS[0],accounts[0], -24082, -24081, liquidity)
#     assert pool.liquidity == liquidity, "current pool liquidity is still liquidity + 1"

#     ## check the math works out to moving the price down 1, sending no amount out, and having some amount remaining
#     (sqrtQ, amountIn, amountOut, feeAmount) = SwapMath.computeSwapStep(
#         p0, p0 - 1, liquidity, 3, FeeAmount.MEDIUM
#     )
#     assert sqrtQ == p0 - 1, "price moves"
#     assert feeAmount == 1, "fee amount is 1"
#     assert amountIn == 1, "amount in is 1"
#     assert amountOut == 0, "zero amount out"


# setFeeProtocol
@pytest.fixture
def initializedSetFeeProtPool(createPoolMedium):
    pool, _, _, _, _ = createPoolMedium
    pool.initialize(encodePriceSqrt(1, 1))
    return createPoolMedium


def test_failsFeeLt4OrGt10(initializedSetFeeProtPool, accounts):
    print("fails if fee is lt 4 or gt 10")
    pool, _, _, _, _ = initializedSetFeeProtPool
    tryExceptHandler(pool.setFeeProtocol, "", 3, 3)
    tryExceptHandler(pool.setFeeProtocol, "", 6, 3)
    tryExceptHandler(pool.setFeeProtocol, "", 3, 6)
    tryExceptHandler(pool.setFeeProtocol, "", 11, 11)
    tryExceptHandler(pool.setFeeProtocol, "", 6, 11)
    tryExceptHandler(pool.setFeeProtocol, "", 11, 6)


def test_setFeeProtocol_4(initializedSetFeeProtPool):
    print("succeeds for fee of 4")
    pool, _, _, _, _ = initializedSetFeeProtPool
    pool.setFeeProtocol(4, 4)


def test_setFeeProtocol_10(initializedSetFeeProtPool):
    print("succeeds for fee of 10")
    pool, _, _, _, _ = initializedSetFeeProtPool
    pool.setFeeProtocol(10, 10)


def test_setFeeProtocol_7(initializedSetFeeProtPool):
    print("succeeds for fee of 7")
    pool, _, _, _, _ = initializedSetFeeProtPool
    pool.setFeeProtocol(7, 7)
    assert pool.slot0.feeProtocol == 119


def test_changeProtocolFee(initializedSetFeeProtPool):
    print("can change protocol fee")
    pool, _, _, _, _ = initializedSetFeeProtPool
    pool.setFeeProtocol(7, 7)
    pool.setFeeProtocol(5, 8)
    assert pool.slot0.feeProtocol == 133


def test_turnOffProtocolFee(initializedSetFeeProtPool):
    print("can turn off protocol fee")
    pool, _, _, _, _ = initializedSetFeeProtPool
    pool.setFeeProtocol(4, 4)
    pool.setFeeProtocol(0, 0)
    assert pool.slot0.feeProtocol == 0


def test_turnOnProtocolFee_returns(initializedSetFeeProtPool):
    print("returns when turned on")
    pool, _, _, _, _ = initializedSetFeeProtPool
    feeProtocolOld0, feeProtocolOld1, feeProtocol0, feeProtocol1 = pool.setFeeProtocol(
        7, 7
    )
    assert feeProtocolOld0 == 0
    assert feeProtocolOld1 == 0
    assert feeProtocol0 == 7
    assert feeProtocol1 == 7


def test_turnOffProtocolFee_returns(initializedSetFeeProtPool):
    print("returns when turned off")
    pool, _, _, _, _ = initializedSetFeeProtPool
    pool.setFeeProtocol(7, 5)
    feeProtocolOld0, feeProtocolOld1, feeProtocol0, feeProtocol1 = pool.setFeeProtocol(
        0, 0
    )
    assert feeProtocolOld0 == 7
    assert feeProtocolOld1 == 5
    assert feeProtocol0 == 0
    assert feeProtocol1 == 0


def test_changeProtocolFee_returns(initializedSetFeeProtPool):
    print("returns when changed")
    pool, _, _, _, _ = initializedSetFeeProtPool
    pool.setFeeProtocol(4, 10)
    feeProtocolOld0, feeProtocolOld1, feeProtocol0, feeProtocol1 = pool.setFeeProtocol(
        6, 8
    )
    assert feeProtocolOld0 == 4
    assert feeProtocolOld1 == 10
    assert feeProtocol0 == 6
    assert feeProtocol1 == 8


def test_unchangedProtocolFee_returns(initializedSetFeeProtPool):
    print("returns when unchanged")
    pool, _, _, _, _ = initializedSetFeeProtPool
    pool.setFeeProtocol(5, 9)
    feeProtocolOld0, feeProtocolOld1, feeProtocol0, feeProtocol1 = pool.setFeeProtocol(
        5, 9
    )
    assert feeProtocolOld0 == 5
    assert feeProtocolOld1 == 9
    assert feeProtocol0 == 5
    assert feeProtocol1 == 9


# fees overflow scenarios => they seem to test the feeGrowth overflow in the
# flash function so we can skip those tests.


# Swap underpayment tests => we don't really need to replicate those since we don't
# use callbacks, we just do the transfer in the pool itself. However, it is useful to
# check that we can't transfer more than the balances


@pytest.fixture
def initializedPoolSwapBalances(initializedSetFeeProtPool, accounts):
    pool, _, _, _, _ = initializedSetFeeProtPool
    iniTick = pool.slot0.tick
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], iniTick, expandTo18Decimals(1))
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], iniTick, expandTo18Decimals(1))
    return initializedSetFeeProtPool


def test_enoughBalance_token0(initializedPoolSwapBalances, accounts, ledger):
    print("swapper swaps all token0")
    pool, _, _, _, _ = initializedPoolSwapBalances
    # Change current tick so it picks up the LO placed on pool.slot0.tick
    pool.slot0.tick = -pool.tickSpacing
    swapExact0For1(
        pool, ledger.balanceOf(accounts[2], TEST_TOKENS[0]), accounts[2], None
    )
    assert ledger.balanceOf(accounts[2], TEST_TOKENS[0]) == 0


def test_enoughBalance_token1(initializedPoolSwapBalances, accounts, ledger):
    print("swapper doesn't have enough token0")
    pool, _, _, _, _ = initializedPoolSwapBalances

    swapExact1For0(
        pool, ledger.balanceOf(accounts[2], TEST_TOKENS[1]), accounts[2], None
    )
    assert ledger.balanceOf(accounts[2], TEST_TOKENS[1]) == 0


def test_notEnoughBalance_token0(initializedPoolSwapBalances, accounts, ledger):
    print("swapper doesn't have enough token0")
    pool, _, _, _, _ = initializedPoolSwapBalances
    initialBalanceToken0 = ledger.balanceOf(accounts[2], TEST_TOKENS[0])
    # Change current tick so it picks up the LO placed on pool.slot0.tick
    pool.slot0.tick = -pool.tickSpacing
    tryExceptHandler(
        swapExact0For1,
        "Insufficient balance",
        pool,
        ledger.balanceOf(accounts[2], TEST_TOKENS[0]) + 1,
        accounts[2],
        None,
    )
    assert ledger.balanceOf(accounts[2], TEST_TOKENS[0]) == initialBalanceToken0


def test_notEnoughBalance_token1(initializedPoolSwapBalances, accounts, ledger):
    print("swapper doesn't have enough token1")
    pool, _, _, _, _ = initializedPoolSwapBalances
    initialBalanceToken1 = ledger.balanceOf(accounts[2], TEST_TOKENS[1])
    tryExceptHandler(
        swapExact1For0,
        "Insufficient balance",
        copy.deepcopy(pool),
        ledger.balanceOf(accounts[2], TEST_TOKENS[1]) + 1,
        accounts[2],
        None,
    )
    assert ledger.balanceOf(accounts[2], TEST_TOKENS[1]) == initialBalanceToken1


# Extra tests since there are modifications in the python ChainflipPool

# Due to the difference in mappings between the python and the solidity we
# have added an assertion when positions don't exist (to not create it)
def test_fails_collectEmpty(createPoolMedium, accounts):
    print("Cannot collect a non-existent position")
    pool, minTick, maxTick, _, _ = createPoolMedium
    tryExceptHandler(
        pool.collectLimitOrder,
        "Position doesn't exist",
        accounts[0],
        TEST_TOKENS[0],
        pool.slot0.tick,
        0,
        0,
    )
    tryExceptHandler(
        pool.collectLimitOrder,
        "Position doesn't exist",
        accounts[0],
        TEST_TOKENS[0],
        minTick,
        1,
        1,
    )
    tryExceptHandler(
        pool.collectLimitOrder,
        "Position doesn't exist",
        accounts[0],
        TEST_TOKENS[0],
        maxTick,
        1,
        1,
    )
    tryExceptHandler(
        pool.collectLimitOrder,
        "Position doesn't exist",
        accounts[0],
        TEST_TOKENS[0],
        0,
        0,
        0,
    )

    tryExceptHandler(
        pool.collectLimitOrder,
        "Position doesn't exist",
        accounts[0],
        TEST_TOKENS[1],
        pool.slot0.tick,
        0,
        0,
    )
    tryExceptHandler(
        pool.collectLimitOrder,
        "Position doesn't exist",
        accounts[0],
        TEST_TOKENS[1],
        minTick,
        1,
        1,
    )
    tryExceptHandler(
        pool.collectLimitOrder,
        "Position doesn't exist",
        accounts[0],
        TEST_TOKENS[1],
        maxTick,
        1,
        1,
    )
    tryExceptHandler(
        pool.collectLimitOrder,
        "Position doesn't exist",
        accounts[0],
        TEST_TOKENS[1],
        0,
        0,
        0,
    )


def test_collectEmpty_noPositionCreated_emptyPool(createPoolMedium, accounts):
    print(
        "Check that new positions are not created (reverts) when we collect an empty position"
    )
    pool, _, _, _, _ = createPoolMedium
    assert pool.ticksLimitTokens0 == {}
    assert pool.ticksLimitTokens1 == {}
    tryExceptHandler(
        pool.collectLimitOrder,
        "Position doesn't exist",
        accounts[0],
        TEST_TOKENS[0],
        pool.slot0.tick,
        0,
        0,
    )
    tryExceptHandler(
        pool.collectLimitOrder,
        "Position doesn't exist",
        accounts[0],
        TEST_TOKENS[1],
        pool.slot0.tick,
        0,
        0,
    )
    # Check that no position has been created
    assert pool.ticksLimitTokens0 == {}
    assert pool.ticksLimitTokens1 == {}


def test_collectEmpty_noPositionCreated_initializedPool(
    mediumPoolInitializedAtZero, accounts
):
    print(
        "Check that new positions are not created (reverts) when we collect an empty position"
    )
    pool, minTick, maxTick, _, _ = mediumPoolInitializedAtZero
    initialTicks0 = copy.deepcopy(pool.ticksLimitTokens0)
    initialTicks1 = copy.deepcopy(pool.ticksLimitTokens1)
    tryExceptHandler(
        pool.collectLimitOrder,
        "Position doesn't exist",
        accounts[0],
        TEST_TOKENS[0],
        minTick,
        0,
        0,
    )
    tryExceptHandler(
        pool.collectLimitOrder,
        "Position doesn't exist",
        accounts[0],
        TEST_TOKENS[0],
        maxTick,
        0,
        0,
    )
    tryExceptHandler(
        pool.collectLimitOrder,
        "Position doesn't exist",
        accounts[0],
        TEST_TOKENS[1],
        minTick,
        0,
        0,
    )
    tryExceptHandler(
        pool.collectLimitOrder,
        "Position doesn't exist",
        accounts[0],
        TEST_TOKENS[1],
        maxTick,
        0,
        0,
    )
    # Check that no position has been created
    assert initialTicks0 == pool.ticksLimitTokens0
    assert initialTicks1 == pool.ticksLimitTokens1


# Not allow burning >0 in a non-existent position
def test_burnGtZero_noPositionCreated_initializedPool(createPoolMedium, accounts):
    print(
        "test that burn > 0 a non-existent position doesn't create a new position(reverts)"
    )
    pool, minTick, maxTick, _, _ = createPoolMedium
    initialTicks = pool.ticks
    tryExceptHandler(
        pool.burnLimitOrder,
        "Position doesn't exist",
        TEST_TOKENS[0],
        accounts[1],
        minTick,
        1,
    )
    tryExceptHandler(
        pool.burnLimitOrder,
        "Position doesn't exist",
        TEST_TOKENS[1],
        accounts[1],
        maxTick,
        1,
    )

    assert initialTicks == pool.ticks


# Allow burning zero in an existing position (poke) but make sure no new position is created if
# burn zero is done on a non-existent position
def test_burnZero_noPositionCreated_initializedPool(createPoolMedium, accounts):
    print(
        "test that burn zero (== poke) a non-existent position doesn't create a new position(reverts)"
    )
    pool, minTick, maxTick, _, _ = createPoolMedium
    initialTicks = pool.ticks
    tryExceptHandler(
        pool.burnLimitOrder,
        "Position doesn't exist",
        TEST_TOKENS[0],
        accounts[1],
        minTick,
        0,
    )
    tryExceptHandler(
        pool.burnLimitOrder,
        "Position doesn't exist",
        TEST_TOKENS[1],
        accounts[1],
        minTick,
        0,
    )
    assert initialTicks == pool.ticks


##########################################################################################
##########################################################################################
######################## Tests added for limit orders ####################################
##########################################################################################
##########################################################################################

# Initial tick == -23028
# Initially no LO


def test_swap0For1_partialSwap(initializedMediumPoolNoLO, accounts):
    print("swap a partial LO zeroForOne")
    (
        pool,
        _,
        _,
        _,
        tickSpacing,
        closeAligniniTickiRDown,
        closeAligniniTickRUp,
    ) = initializedMediumPoolNoLO

    iniLiquidity = pool.liquidity
    iniSlot0 = pool.slot0

    tickLO = closeAligniniTickRUp + tickSpacing * 10
    liquidityPosition = expandTo18Decimals(1)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], tickLO, liquidityPosition)
    amountToSwap = expandTo18Decimals(1) // 10

    (
        _,
        amount0,
        amount1,
        sqrtPriceX96,
        liquidity,
        tick,
    ) = swapExact0For1(pool, amountToSwap, accounts[0], None)

    # This should have partially swapped the limit order placed
    priceLO = TickMath.getPriceAtTick(tickLO)
    # Pool has been initialized at around 1 : 10.
    priceIni = TickMath.getPriceAtTick(-23028)
    priceCloseTickUp = TickMath.getPriceAtTick(closeAligniniTickRUp)

    # The price of tickLO should be a bit above the initialized price (tickSpacing*10) and the closest tick up
    # Here we are just comparing sqrtPrices, but that good.
    assert priceLO > priceCloseTickUp
    assert priceLO > priceIni

    ## Check swap outcomes
    # Tick, sqrtPrice and liquidity haven't changed (range order pool)
    assert pool.liquidity == iniLiquidity == liquidity
    assert pool.slot0 == iniSlot0
    assert pool.slot0.sqrtPriceX96 == sqrtPriceX96
    assert pool.slot0.tick == tick

    check_limitOrderSwap_oneTick_exactIn(
        pool,
        getLimitPositionKey(accounts[0], tickLO, False),
        tickLO,
        amountToSwap,
        liquidityPosition,
        amount0,
        amount1,
        True,
        SwapMath.ONE_IN_PIPS,
        priceLO,
    )

    return pool, tickLO, priceLO, amountToSwap, amount1, liquidityPosition


def test_swap1For0_partialSwap(initializedMediumPoolNoLO, accounts):
    print("swap a partial LO not zeroForOne")
    (
        pool,
        _,
        _,
        _,
        tickSpacing,
        closeAligniniTickiRDown,
        closeAligniniTickRUp,
    ) = initializedMediumPoolNoLO

    iniLiquidity = pool.liquidity
    iniSlot0 = pool.slot0

    tickLO = closeAligniniTickiRDown - tickSpacing * 10
    liquidityPosition = expandTo18Decimals(1)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], tickLO, liquidityPosition)
    # Due to the pool price we need to swap a lot less
    amountToSwap = expandTo18Decimals(1) // 15

    (
        _,
        amount0,
        amount1,
        sqrtPriceX96,
        liquidity,
        tick,
    ) = swapExact1For0(pool, amountToSwap, accounts[0], None)

    # This should have partially swapped the limit order placed
    priceLO = TickMath.getPriceAtTick(tickLO)
    # Pool has been initialized at around 1 : 10.
    priceIni = TickMath.getPriceAtTick(-23028)
    priceCloseTickUp = TickMath.getPriceAtTick(closeAligniniTickiRDown)

    # The price of tickLO should be a bit above the initialized price (tickSpacing*10) and the closest tick up
    # Here we are just comparing sqrtPrices, but that good.
    assert priceLO < priceCloseTickUp
    assert priceLO < priceIni

    ## Check swap outcomes
    # Tick, sqrtPrice and liquidity haven't changed (range order pool)
    assert pool.liquidity == iniLiquidity == liquidity
    assert pool.slot0 == iniSlot0
    assert pool.slot0.sqrtPriceX96 == sqrtPriceX96
    assert pool.slot0.tick == tick

    check_limitOrderSwap_oneTick_exactIn(
        pool,
        getLimitPositionKey(accounts[0], tickLO, True),
        tickLO,
        amountToSwap,
        liquidityPosition,
        amount1,
        amount0,
        False,
        SwapMath.ONE_IN_PIPS,
        priceLO,
    )

    return pool, tickLO, priceLO, amountToSwap, amount0, liquidityPosition


def test_mintWorseLO_zeroForOne(initializedMediumPoolNoLO, accounts):
    print("check that LO with bad pricing is not used - zeroForOne")
    pool, _, _, _, _, closeAligniniTickiRDown, _ = initializedMediumPoolNoLO
    pool.mintLimitOrder(
        TEST_TOKENS[1], accounts[0], closeAligniniTickiRDown, expandTo18Decimals(1)
    )
    test_swap0For1_partialSwap(initializedMediumPoolNoLO, accounts)
    # Check LO position and tick
    assert pool.limitOrders[
        getLimitPositionKey(accounts[0], closeAligniniTickiRDown, False)
    ].liquidity == expandTo18Decimals(1)
    assert pool.ticksLimitTokens1[
        closeAligniniTickiRDown
    ].liquidityLeft == expandTo18Decimals(1)
    assert pool.ticksLimitTokens1[
        closeAligniniTickiRDown
    ].liquidityGross == expandTo18Decimals(1)


def test_mintWorseLO_oneForZero(initializedMediumPoolNoLO, accounts):
    print("check that LO with bad pricing is not used - not zeroForOne")
    pool, _, _, _, _, _, closeAligniniTickRUp = initializedMediumPoolNoLO
    pool.mintLimitOrder(
        TEST_TOKENS[0], accounts[0], closeAligniniTickRUp, expandTo18Decimals(1)
    )
    test_swap1For0_partialSwap(initializedMediumPoolNoLO, accounts)
    # Check LO position and tick
    assert pool.limitOrders[
        getLimitPositionKey(accounts[0], closeAligniniTickRUp, True)
    ].liquidity == expandTo18Decimals(1)
    assert pool.ticksLimitTokens0[
        closeAligniniTickRUp
    ].liquidityLeft == expandTo18Decimals(1)
    assert pool.ticksLimitTokens0[
        closeAligniniTickRUp
    ].liquidityGross == expandTo18Decimals(1)


def test_swap0For1_fullSwap(initializedMediumPoolNoLO, accounts, ledger):
    print("swap a full LO zeroForOne")
    (
        pool,
        _,
        _,
        _,
        tickSpacing,
        closeAligniniTickiRDown,
        closeAligniniTickRUp,
    ) = initializedMediumPoolNoLO

    iniLiquidity = pool.liquidity
    iniSlot0 = pool.slot0

    tickLO = closeAligniniTickRUp + tickSpacing * 10
    tickLO1 = closeAligniniTickRUp + tickSpacing * 2
    initialLiquidity = expandTo18Decimals(1)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[4], tickLO, initialLiquidity)
    pool.mintLimitOrder(
        TEST_TOKENS[1], accounts[1], tickLO1, initialLiquidity
    )  # backup

    # To cross the first tick (=== first position tickL0) and part of the second (tickL01)
    amountToSwap = expandTo18Decimals(1) * 10
    (
        _,
        amount0,
        amount1,
        sqrtPriceX96,
        liquidity,
        tick,
    ) = swapExact0For1(pool, amountToSwap, accounts[0], None)

    # This should have partially swapped the limit order placed
    priceLO = TickMath.getPriceAtTick(tickLO)
    priceLO1 = TickMath.getPriceAtTick(tickLO1)
    # Pool has been initialized at around 1 : 10.
    priceIni = TickMath.getPriceAtTick(-23028)
    priceCloseTickUp = TickMath.getPriceAtTick(closeAligniniTickRUp)

    # The price of tickLO should be a bit above the initialized price (tickSpacing*10) and the closest tick up
    # Here we are just comparing sqrtPrices, but that good.
    assert priceLO > priceCloseTickUp
    assert priceLO > priceIni

    assert priceLO > priceLO1

    ## Check swap outcomes
    # Tick, sqrtPrice and liquidity haven't changed (range order pool)
    assert pool.liquidity == iniLiquidity == liquidity
    assert pool.slot0 == iniSlot0
    assert pool.slot0.sqrtPriceX96 == sqrtPriceX96
    assert pool.slot0.tick == tick

    # Check amounts
    assert amount0 == amountToSwap

    amountRemainingLessFee = (
        (amountToSwap) * (SwapMath.ONE_IN_PIPS - pool.fee) // SwapMath.ONE_IN_PIPS
    )

    amountOut = mulDiv(amountRemainingLessFee, priceLO, 2**96)
    amountOutLO1 = mulDiv(amountRemainingLessFee, priceLO1, 2**96)

    # Part will be swapped from tickLO and part from tickLO1. Price will be worse than if it was fully swapped
    # from tickLO but better than if it was fully swapped in tick LO1
    assert abs(amount1) < amountOut
    assert abs(amount1) > amountOutLO1

    # Check LO position and tick
    assertLimitPositionIsBurnt(pool.limitOrders, accounts[0], tickLO, False)
    assert pool.ticksLimitTokens1[tickLO1].liquidityLeft == initialLiquidity * 2 - abs(
        amount1
    )

    # If all had been swapped at a better price (for the user) there would be less liquidity left
    assert (
        pool.ticksLimitTokens1[tickLO1].liquidityLeft > initialLiquidity * 2 - amountOut
    )
    assert (
        pool.ticksLimitTokens1[tickLO1].liquidityLeft
        < initialLiquidity * 2 - amountOutLO1
    )

    assert (
        initialLiquidity + pool.ticksLimitTokens1[tickLO1].liquidityGross
        == initialLiquidity * 2
    )

    return pool, tickLO, tickLO1, initialLiquidity


def test_swap1For0_fullSwap(initializedMediumPoolNoLO, accounts, ledger):
    print("swap a full LO OneForZero")
    (
        pool,
        _,
        _,
        _,
        tickSpacing,
        closeAligniniTickiRDown,
        closeAligniniTickRUp,
    ) = initializedMediumPoolNoLO

    iniLiquidity = pool.liquidity
    iniSlot0 = pool.slot0

    tickLO = closeAligniniTickiRDown - tickSpacing * 10
    tickLO1 = closeAligniniTickiRDown - tickSpacing * 2
    initialLiquidity = expandTo18Decimals(1)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], tickLO, initialLiquidity)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], tickLO1, initialLiquidity)

    # To cross the first tick (=== first position tickL0) and part of the second (tickL01)
    amountToSwap = expandTo18Decimals(1) // 10
    (
        _,
        amount0,
        amount1,
        sqrtPriceX96,
        liquidity,
        tick,
    ) = swapExact1For0(pool, amountToSwap, accounts[1], None)

    # This should have partially swapped the limit order placed
    priceLO = TickMath.getPriceAtTick(tickLO)
    priceLO1 = TickMath.getPriceAtTick(tickLO1)
    # Pool has been initialized at around 1 : 10.
    priceIni = TickMath.getPriceAtTick(-23028)
    priceCloseTickUp = TickMath.getPriceAtTick(closeAligniniTickiRDown)

    # The price of tickLO should be a bit above the initialized price (tickSpacing*10) and the closest tick up
    # Here we are just comparing sqrtPrices, but that good.
    assert priceLO < priceCloseTickUp
    assert priceLO < priceIni
    assert priceLO < priceLO1

    ## Check swap outcomes
    # Tick, sqrtPrice and liquidity haven't changed (range order pool)
    assert pool.liquidity == iniLiquidity == liquidity
    assert pool.slot0 == iniSlot0
    assert pool.slot0.sqrtPriceX96 == sqrtPriceX96
    assert pool.slot0.tick == tick

    # Check amounts
    assert amount1 == amountToSwap

    amountRemainingLessFee = (
        (amountToSwap) * (SwapMath.ONE_IN_PIPS - pool.fee) // SwapMath.ONE_IN_PIPS
    )

    # Swapped mul/div because the price is token0->token1
    amountOutL0 = mulDiv(amountRemainingLessFee, 2**96, priceLO)
    amountOutLO1 = mulDiv(amountRemainingLessFee, 2**96, priceLO1)

    # Part will be swapped from tickLO and part from tickLO1. Price will be worse than if it was fully swapped
    # from tickLO but better than if it was fully swapped in tick LO1
    assert abs(amount0) < amountOutL0
    assert abs(amount0) > amountOutLO1

    # Check LO position and tick - should have been burnt
    assertLimitPositionIsBurnt(pool.limitOrders, accounts[0], tickLO, True)
    assert pool.limitOrders[
        getLimitPositionKey(accounts[0], tickLO1, True)
    ].liquidity == expandTo18Decimals(1)
    assert pool.ticksLimitTokens0[tickLO1].liquidityLeft == initialLiquidity * 2 - abs(
        amount0
    )

    # If all had been swapped at a better price (for the user) there would be less liquidity left
    assert (
        pool.ticksLimitTokens0[tickLO1].liquidityLeft
        > initialLiquidity * 2 - amountOutL0
    )
    assert (
        pool.ticksLimitTokens0[tickLO1].liquidityLeft
        < initialLiquidity * 2 - amountOutLO1
    )

    assert (
        initialLiquidity + pool.ticksLimitTokens0[tickLO1].liquidityGross
        == initialLiquidity * 2
    )


# Mint multiple positions and check that the correct ones are used
def test_multiplePositions_zeroForOne(initializedMediumPoolNoLO, accounts):
    print("mint multiple positions zeroForOne")
    (
        pool,
        _,
        _,
        _,
        tickSpacing,
        closeAligniniTickiRDown,
        closeAligniniTickRUp,
    ) = initializedMediumPoolNoLO

    tickLO = closeAligniniTickRUp + tickSpacing * 10

    initialLiquidity = expandTo18Decimals(1)

    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], tickLO, initialLiquidity)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[1], tickLO, initialLiquidity)

    # Check tick before swapping
    assert pool.ticksLimitTokens1[tickLO].liquidityLeft == initialLiquidity * 2
    assert pool.ticksLimitTokens1[tickLO].liquidityGross == initialLiquidity * 2

    # To cross the first tick (=== first position tickL0) and part of the second (tickL01)
    amountToSwap = expandTo18Decimals(1) * 10
    (
        _,
        amount0,
        amount1,
        sqrtPriceX96,
        liquidity,
        tick,
    ) = swapExact0For1(pool, amountToSwap, accounts[0], None)

    # This should have partially swapped the limit order placed
    priceLO = TickMath.getPriceAtTick(tickLO)

    # Check amounts
    assert amount0 == amountToSwap

    amountRemainingLessFee = (
        (amountToSwap) * (SwapMath.ONE_IN_PIPS - pool.fee) // SwapMath.ONE_IN_PIPS
    )

    amountOutLO = mulDiv(amountRemainingLessFee, priceLO, 2**96)

    # Part will be swapped from tickLO and part from tickLO1. Price will be worse than if it was fully swapped
    # from tickLO but better than if it was fully swapped in tick LO1
    assert abs(amount1) == amountOutLO

    # Check LO position and tick
    assert pool.limitOrders[
        getLimitPositionKey(accounts[0], tickLO, False)
    ].liquidity == expandTo18Decimals(1)
    assert pool.limitOrders[
        getLimitPositionKey(accounts[1], tickLO, False)
    ].liquidity == expandTo18Decimals(1)
    assert pool.ticksLimitTokens1[tickLO].liquidityLeft == initialLiquidity * 2 - abs(
        amount1
    )
    assert pool.ticksLimitTokens1[tickLO].liquidityGross == initialLiquidity * 2


# Mint multiple positions and check that the correct ones are used
def test_multiplePositions_oneForZero(initializedMediumPoolNoLO, accounts):
    print("mint multiple positions oneForZero")
    (
        pool,
        _,
        _,
        _,
        tickSpacing,
        closeAligniniTickiRDown,
        closeAligniniTickRUp,
    ) = initializedMediumPoolNoLO

    tickLO = closeAligniniTickiRDown - tickSpacing * 10

    initialLiquidity = expandTo18Decimals(1)

    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], tickLO, initialLiquidity)
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[1], tickLO, initialLiquidity)

    # Check tick before swapping
    assert pool.ticksLimitTokens0[tickLO].liquidityLeft == initialLiquidity * 2
    assert pool.ticksLimitTokens0[tickLO].liquidityGross == initialLiquidity * 2

    # To cross the first tick (=== first position tickL0) and part of the second (tickL01)
    amountToSwap = expandTo18Decimals(1) // 10
    (
        _,
        amount0,
        amount1,
        sqrtPriceX96,
        liquidity,
        tick,
    ) = swapExact1For0(pool, amountToSwap, accounts[0], None)

    # This should have partially swapped the limit order placed
    priceLO = TickMath.getPriceAtTick(tickLO)

    # Check amounts
    assert amount1 == amountToSwap

    amountRemainingLessFee = (
        (amountToSwap) * (SwapMath.ONE_IN_PIPS - pool.fee) // SwapMath.ONE_IN_PIPS
    )

    amountOutLO = mulDiv(amountRemainingLessFee, 2**96, priceLO)

    # Part will be swapped from tickLO and part from tickLO1. Price will be worse than if it was fully swapped
    # from tickLO but better than if it was fully swapped in tick LO1
    assert abs(amount0) == amountOutLO

    # Check LO position and tick
    assert pool.limitOrders[
        getLimitPositionKey(accounts[0], tickLO, True)
    ].liquidity == expandTo18Decimals(1)
    assert pool.limitOrders[
        getLimitPositionKey(accounts[1], tickLO, True)
    ].liquidity == expandTo18Decimals(1)
    assert pool.ticksLimitTokens0[tickLO].liquidityLeft == initialLiquidity * 2 - abs(
        amount0
    )
    assert pool.ticksLimitTokens0[tickLO].liquidityGross == initialLiquidity * 2


def test_mint_partialSwappedTick_zeroForOne(initializedMediumPoolNoLO, accounts):
    print("mint a new position on top of a half-swapped tick zeroForOne")
    (
        pool,
        tickLO,
        priceLO,
        amountToSwap,
        amount1,
        liquidityPosition,
    ) = test_swap0For1_partialSwap(initializedMediumPoolNoLO, accounts)

    iniLiquidityGross = pool.ticksLimitTokens1[tickLO].liquidityGross
    assert iniLiquidityGross == liquidityPosition
    iniLiquidityLeft = pool.ticksLimitTokens1[tickLO].liquidityLeft
    assert iniLiquidityGross > 0
    assert iniLiquidityLeft > 0

    pool.mintLimitOrder(TEST_TOKENS[1], accounts[1], tickLO, expandTo18Decimals(1))

    assert pool.ticksLimitTokens1[
        tickLO
    ].liquidityGross == iniLiquidityGross + expandTo18Decimals(1)
    assert pool.ticksLimitTokens1[
        tickLO
    ].liquidityLeft == iniLiquidityLeft + expandTo18Decimals(1)

    assert pool.limitOrders[
        getLimitPositionKey(accounts[1], tickLO, False)
    ].liquidity == expandTo18Decimals(1)

    return pool, tickLO, priceLO, amountToSwap, amount1, liquidityPosition


def test_mint_partialSwappedTick_oneForZero(initializedMediumPoolNoLO, accounts):
    print("mint a new position on top of a half-swapped tick oneForZero")
    (
        pool,
        tickLO,
        priceLO,
        amountToSwap,
        amount0,
        liquidityPosition,
    ) = test_swap1For0_partialSwap(initializedMediumPoolNoLO, accounts)

    iniLiquidityGross = pool.ticksLimitTokens0[tickLO].liquidityGross
    assert iniLiquidityGross == liquidityPosition
    iniLiquidityLeft = pool.ticksLimitTokens0[tickLO].liquidityLeft
    assert iniLiquidityGross > 0
    assert iniLiquidityLeft > 0

    pool.mintLimitOrder(TEST_TOKENS[0], accounts[1], tickLO, expandTo18Decimals(1))

    assert pool.ticksLimitTokens0[
        tickLO
    ].liquidityGross == iniLiquidityGross + expandTo18Decimals(1)
    assert pool.ticksLimitTokens0[
        tickLO
    ].liquidityLeft == iniLiquidityLeft + expandTo18Decimals(1)

    assert pool.limitOrders[
        getLimitPositionKey(accounts[1], tickLO, True)
    ].liquidity == expandTo18Decimals(1)
    return pool, tickLO, priceLO, amountToSwap, amount0, liquidityPosition


# # TODO: Minting on top of a fullySwapped Tick won't work for now. Force burning of the tick/positions? TO THINK.


def test_mint_fullSwappedTick_zeroForOne_diffAccount(
    initializedMediumPoolNoLO, accounts, ledger
):
    print(
        "mint a new position with another account on top of a full-swapped tick zeroForOne and burn it"
    )
    (
        pool,
        tickLO,  # fullySwapped
        tickLO1,  # partiallySwapped
        initialLiquidity,
    ) = test_swap0For1_fullSwap(initializedMediumPoolNoLO, accounts, ledger)

    # Check that tickLO is partially swapped and not removed
    assert pool.ticksLimitTokens1[tickLO1].liquidityLeft > 0
    assert pool.ticksLimitTokens1[tickLO1].liquidityGross > 0

    # Mint a position on top of tickLO (another account)
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[5], tickLO, initialLiquidity)

    # Set the pool to the initial tick
    pool.slot0.tick = -23028

    amountToSwap = expandTo18Decimals(1) * 10
    # This will fully swap the newly minted position and part of the backup LO1 position
    swapExact0For1(pool, amountToSwap, accounts[3], None)

    # Check that the newly minted pos and the old one return same amount of tokens and fees.
    # Final balances should be same.
    assert ledger.balanceOf(accounts[5], TEST_TOKENS[0]) == ledger.balanceOf(
        accounts[4], TEST_TOKENS[0]
    )
    assert ledger.balanceOf(accounts[5], TEST_TOKENS[1]) == ledger.balanceOf(
        accounts[4], TEST_TOKENS[1]
    )


def test_burn_positionMintedAfterSwap_zeroForOne(initializedMediumPoolNoLO, accounts):
    print(
        "Mint a position, swap, mint another one on top, and burn+collect them - zeroForOne"
    )

    # This mints a LO on top of a half-swapped tick
    (
        pool,
        tickLO,
        priceLO,
        amountToSwap,
        amountSwapped,
        liquidityPosition,
    ) = test_mint_partialSwappedTick_zeroForOne(initializedMediumPoolNoLO, accounts)

    # Burn newly minted position
    check_burn_limitOrderSwap_oneTick_exactIn(
        pool, accounts[1], tickLO, liquidityPosition, 0, True, priceLO, False
    )

    # Check amounts - same check as in test_swap0For1_partialSwap for the first minted position. Nothing
    # should have changed by minting and burning an extra position on top after the swap has taken place.
    check_limitOrderSwap_oneTick_exactIn(
        pool,
        getLimitPositionKey(accounts[0], tickLO, False),
        tickLO,
        amountToSwap,
        liquidityPosition,
        amountToSwap,
        amountSwapped,
        True,
        SwapMath.ONE_IN_PIPS,
        priceLO,
    )

    # Burn first position (partially swapped)
    check_burn_limitOrderSwap_oneTick_exactIn(
        pool, accounts[0], tickLO, liquidityPosition, amountSwapped, True, priceLO, True
    )


def test_burn_positionMintedAfterSwap_oneForZero(initializedMediumPoolNoLO, accounts):
    print(
        "Mint a position, swap, mint another one on top, and burn+collect them, oneForZero"
    )
    # This mints a LO on top of a half-swapped tick
    (
        pool,
        tickLO,
        priceLO,
        amountToSwap,
        amountSwapped,
        liquidityPosition,
    ) = test_mint_partialSwappedTick_oneForZero(initializedMediumPoolNoLO, accounts)

    # Burn newly minted position
    check_burn_limitOrderSwap_oneTick_exactIn(
        pool, accounts[1], tickLO, liquidityPosition, 0, False, priceLO, False
    )

    # Check amounts - same check as in test_swap1For0_partialSwap for the first minted position. Nothing
    # should have changed by minting and burning an extra position on top after the swap has taken place.
    check_limitOrderSwap_oneTick_exactIn(
        pool,
        getLimitPositionKey(accounts[0], tickLO, True),
        tickLO,
        amountToSwap,
        liquidityPosition,
        amountToSwap,
        amountSwapped,
        False,
        SwapMath.ONE_IN_PIPS,
        priceLO,
    )

    # Burn first position (partially swapped)
    check_burn_limitOrderSwap_oneTick_exactIn(
        pool,
        accounts[0],
        tickLO,
        liquidityPosition,
        amountSwapped,
        False,
        priceLO,
        True,
    )


def test_mintSwapBurn_partialSwappedTick_zeroForOne(
    initializedMediumPoolNoLO, accounts
):
    print("mint a new position on top of a half-swapped tick zeroForOne, swap and burn")
    (
        pool,
        tickLO,
        priceLO,
        amountToSwap,
        amount1,
        liquidityPosition,
    ) = test_swap0For1_partialSwap(initializedMediumPoolNoLO, accounts)

    iniAmountPercSwappedInsideX128 = pool.ticksLimitTokens1[
        tickLO
    ].amountPercSwappedInsideX128
    iniLiquidityLeft = pool.ticksLimitTokens1[tickLO].liquidityLeft

    pool.mintLimitOrder(TEST_TOKENS[1], accounts[1], tickLO, expandTo18Decimals(1) * 2)

    # Check minting amounts
    assert (
        iniAmountPercSwappedInsideX128
        == pool.ticksLimitTokens1[tickLO].amountPercSwappedInsideX128
    )
    assert (
        pool.ticksLimitTokens1[tickLO].liquidityLeft
        == iniLiquidityLeft + expandTo18Decimals(1) * 2
    )
    iniLiquidityLeft = pool.ticksLimitTokens1[tickLO].liquidityLeft

    # Make sure it's a different percentatge than the first swap
    amountToSwap2 = expandTo18Decimals(1) // 12

    (
        _,
        amount0,
        amount1,
        _,
        _,
        _,
    ) = swapExact0For1(pool, amountToSwap2, accounts[0], None)

    # Check that the final math makes sense
    currentPercSwapped = mulDiv(
        abs(amount1),
        FixedPoint128_Q128,
        iniLiquidityLeft,
    )

    # Amount POS0
    pos0 = pool.limitOrders[getLimitPositionKey(accounts[0], tickLO, False)]
    # Hardcore calculation - swap by swap
    amountPos0Swapped = mulDiv(
        pos0.liquidity, (iniAmountPercSwappedInsideX128 - 0), FixedPoint128_Q128
    ) + mulDiv(
        mulDiv(
            pos0.liquidity,
            (FixedPoint128_Q128 - iniAmountPercSwappedInsideX128),
            FixedPoint128_Q128,
        ),
        currentPercSwapped,
        FixedPoint128_Q128,
    )

    amountPos0Left = pos0.liquidity - amountPos0Swapped
    amountPos0SwappedToken = mulDiv(abs(amountPos0Swapped), 2**96, priceLO)

    # Total amount of swapped tokens match initial liquidity
    assert expandTo18Decimals(1) == amountPos0Left + amountPos0Swapped

    # Amount POS1
    pos1 = pool.limitOrders[getLimitPositionKey(accounts[1], tickLO, False)]
    # Hardcore calculation - swap by swap - only one swap
    amountPos1Swapped = mulDiv(pos1.liquidity, currentPercSwapped, FixedPoint128_Q128)

    amountPos1Left = pos1.liquidity - amountPos1Swapped
    amountPos1SwappedToken = mulDiv(abs(amountPos1Swapped), 2**96, priceLO)

    # Total amount of swapped tokens match initial liquidity and the amount swapped
    assert expandTo18Decimals(2) == amountPos1Left + amountPos1Swapped

    amountSwappedMinusFees = mulDiv(
        amountToSwap + amountToSwap2,
        SwapMath.ONE_IN_PIPS - pool.fee,
        SwapMath.ONE_IN_PIPS,
    )
    # Small error (31*10^-18) due to rounding
    assert (
        amountSwappedMinusFees == amountPos0SwappedToken + amountPos1SwappedToken + 31
    )

    # Burn limit orders
    (_, _, amount, amountBurnt0, amountBurnt1) = pool.burnLimitOrder(
        TEST_TOKENS[1], accounts[0], tickLO, expandTo18Decimals(1)
    )
    # TODO: Check that this margin (diff) is acceptable
    assert amountPos0Left - 2 == amountBurnt1
    assert amountPos0SwappedToken + 19 == amountBurnt0

    (_, _, amount, amountBurnt0, amountBurnt1) = pool.burnLimitOrder(
        TEST_TOKENS[1], accounts[1], tickLO, expandTo18Decimals(2)
    )

    # TODO: Check that this margin (diff) is acceptable
    assert amountPos1Left - 1 == amountBurnt1
    assert amountPos1SwappedToken + 9 == amountBurnt0


def test_mintSwapBurn_partialSwappedTick_oneForZero(
    initializedMediumPoolNoLO, accounts
):
    print("mint a new position on top of a half-swapped tick oneForZero, swap and burn")
    (
        pool,
        tickLO,
        priceLO,
        amountToSwap,
        amount1,
        liquidityPosition,
    ) = test_swap1For0_partialSwap(initializedMediumPoolNoLO, accounts)

    iniAmountPercSwappedInsideX128 = pool.ticksLimitTokens0[
        tickLO
    ].amountPercSwappedInsideX128
    iniLiquidityLeft = pool.ticksLimitTokens0[tickLO].liquidityLeft

    pool.mintLimitOrder(TEST_TOKENS[0], accounts[1], tickLO, expandTo18Decimals(1) * 2)

    # Check minting amounts
    assert (
        iniAmountPercSwappedInsideX128
        == pool.ticksLimitTokens0[tickLO].amountPercSwappedInsideX128
    )
    assert (
        pool.ticksLimitTokens0[tickLO].liquidityLeft
        == iniLiquidityLeft + expandTo18Decimals(1) * 2
    )
    iniLiquidityLeft = pool.ticksLimitTokens0[tickLO].liquidityLeft

    # Make sure it's a different percentatge than the first swap
    amountToSwap2 = expandTo18Decimals(1) // 12

    (
        _,
        amount0,
        amount1,
        _,
        _,
        _,
    ) = swapExact1For0(pool, amountToSwap2, accounts[0], None)

    # Check that the final math makes sense
    currentPercSwapped = mulDiv(
        abs(amount0),
        FixedPoint128_Q128,
        iniLiquidityLeft,
    )

    # Amount POS0
    pos0 = pool.limitOrders[getLimitPositionKey(accounts[0], tickLO, True)]
    # Hardcore calculation - swap by swap
    amountPos0Swapped = mulDiv(
        pos0.liquidity, (iniAmountPercSwappedInsideX128 - 0), FixedPoint128_Q128
    ) + mulDiv(
        mulDiv(
            pos0.liquidity,
            (FixedPoint128_Q128 - iniAmountPercSwappedInsideX128),
            FixedPoint128_Q128,
        ),
        currentPercSwapped,
        FixedPoint128_Q128,
    )

    amountPos0Left = pos0.liquidity - amountPos0Swapped
    amountPos0SwappedToken = mulDiv(abs(amountPos0Swapped), priceLO, 2**96)

    # Total amount of swapped tokens match initial liquidity
    assert expandTo18Decimals(1) == amountPos0Left + amountPos0Swapped

    # Amount POS1
    pos1 = pool.limitOrders[getLimitPositionKey(accounts[1], tickLO, True)]
    # Hardcore calculation - swap by swap - only one swap
    amountPos1Swapped = mulDiv(pos1.liquidity, currentPercSwapped, FixedPoint128_Q128)

    amountPos1Left = pos1.liquidity - amountPos1Swapped
    amountPos1SwappedToken = mulDiv(abs(amountPos1Swapped), priceLO, 2**96)

    # Total amount of swapped tokens match initial liquidity and the amount swapped
    assert expandTo18Decimals(2) == amountPos1Left + amountPos1Swapped

    amountSwappedMinusFees = mulDiv(
        amountToSwap + amountToSwap2,
        SwapMath.ONE_IN_PIPS - pool.fee,
        SwapMath.ONE_IN_PIPS,
    )
    # Small error (1*10^-18) due to rounding
    assert amountSwappedMinusFees == amountPos0SwappedToken + amountPos1SwappedToken + 1

    # Burn limit orders
    (_, _, amount, amountBurnt0, amountBurnt1) = pool.burnLimitOrder(
        TEST_TOKENS[0], accounts[0], tickLO, expandTo18Decimals(1)
    )
    # TODO: Check that this margin (diff) is acceptable
    assert amountPos0Left - 2 == amountBurnt0
    assert amountPos0SwappedToken == amountBurnt1

    (_, _, amount, amountBurnt0, amountBurnt1) = pool.burnLimitOrder(
        TEST_TOKENS[0], accounts[1], tickLO, expandTo18Decimals(2)
    )

    # TODO: Check that this margin (diff) is acceptable
    assert amountPos1Left - 1 == amountBurnt0
    assert amountPos1SwappedToken == amountBurnt1


def test_limitOrder_currentTick(initializedPoolMedium12TickSpacing, accounts):
    print("current orders on current tick")
    pool, _, _, _, _ = initializedPoolMedium12TickSpacing
    # Tick == 0
    initick = pool.slot0.tick

    assert pool.ticksLimitTokens0 == {}
    assert pool.ticksLimitTokens1 == {}

    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], initick, expandTo18Decimals(1))
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], initick, expandTo18Decimals(1))

    tick0 = pool.ticksLimitTokens0[initick]
    tick1 = pool.ticksLimitTokens1[initick]
    assert tick0.liquidityGross == tick0.liquidityLeft == expandTo18Decimals(1)
    assert tick1.liquidityGross == tick1.liquidityLeft == expandTo18Decimals(1)

    # In one direction the limit order is taken
    swapExact1For0(pool, expandTo18Decimals(1), accounts[0], None)

    assert initick == pool.slot0.tick

    assert tick0.liquidityGross == expandTo18Decimals(1)
    # Should be almost zero (since there are fees). Just checking that it has been used.
    assert tick0.liquidityLeft < expandTo18Decimals(1)
    assert tick1.liquidityGross == tick1.liquidityLeft == expandTo18Decimals(1)

    # In the other direction it is taken but not until the range orders don't change the
    # pool price
    swapExact0For1(pool, expandTo18Decimals(1), accounts[0], None)

    assert initick != pool.slot0.tick
    # Not ending at the border (MIN_TICK) but rather going to the next best LO tick - 1
    assert pool.slot0.tick == initick - 1

    # Tick 0 not altered
    assert tick0.liquidityGross == expandTo18Decimals(1)
    assert tick0.liquidityLeft < expandTo18Decimals(1)
    # Tick1 used
    assert tick1.liquidityGross == expandTo18Decimals(1)
    # Should be almost zero (since there are fees). Just checking that it has been used.
    assert tick1.liquidityLeft < expandTo18Decimals(1)

    assert tick0.liquidityLeft == tick1.liquidityLeft


def test_noRangeOrder_limitOrderWorsePrice_token0(
    initializedPoolMedium12TickSpacing, accounts
):
    print("token0 LO worse than current price")
    pool, _, _, _, _ = initializedPoolMedium12TickSpacing

    # Tick == 0
    initick = pool.slot0.tick
    tickLO = initick + pool.tickSpacing * 10

    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], tickLO, expandTo18Decimals(1))

    tick0 = pool.ticksLimitTokens0[tickLO]
    assert tick0.liquidityGross == tick0.liquidityLeft == expandTo18Decimals(1)

    # In the other direction it is taken but not until the range orders don't change the
    # pool price
    swapExact1For0(pool, expandTo18Decimals(1), accounts[0], None)

    assert initick != pool.slot0.tick
    # Not ending at the border (MIN_TICK) but rather going to the next best LO tick - 1
    assert pool.slot0.tick == tickLO

    # Tick0 used
    assert tick0.liquidityGross == expandTo18Decimals(1)
    # Should be almost zero (since there are fees). Just checking that it has been used.
    assert tick0.liquidityLeft < expandTo18Decimals(1)


# For token1 similar test to test_limitOrder_currentTick
def test_noRangeOrder_limitOrderWorsePrice_token1(
    initializedPoolMedium12TickSpacing, accounts
):
    print("token1 LO worse than current price")
    pool, _, _, _, _ = initializedPoolMedium12TickSpacing

    # Tick == 0
    initick = pool.slot0.tick
    tickLO = initick - pool.tickSpacing * 10

    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], tickLO, expandTo18Decimals(1))

    tick1 = pool.ticksLimitTokens1[tickLO]
    assert tick1.liquidityGross == tick1.liquidityLeft == expandTo18Decimals(1)

    # In the other direction it is taken but not until the range orders don't change the
    # pool price
    swapExact0For1(pool, expandTo18Decimals(1), accounts[0], None)

    assert initick != pool.slot0.tick
    # Not ending at the border (MIN_TICK) but rather going to the next best LO tick - 1
    assert pool.slot0.tick == tickLO - 1

    # Tick1 used
    assert tick1.liquidityGross == expandTo18Decimals(1)
    # Should be almost zero (since there are fees). Just checking that it has been used.
    assert tick1.liquidityLeft < expandTo18Decimals(1)


def test_burnPartiallySwapped_multipleSteps_zeroForOne(
    initializedMediumPoolNoLO, accounts
):
    print("burn partially swapped positions in multiple steps - zeroForOne")
    (
        pool,
        tickLO,
        priceLO,
        amountToSwap,
        amount1,
        liquidityPosition,
    ) = test_swap0For1_partialSwap(initializedMediumPoolNoLO, accounts)

    poolCopy = copy.deepcopy(pool)

    (_, _, amount, correctAmountBurnt0, correctAmountBurnt1) = poolCopy.burnLimitOrder(
        TEST_TOKENS[1], accounts[0], tickLO, expandTo18Decimals(1)
    )

    tryExceptHandler(
        poolCopy.burnLimitOrder,
        "LS",
        TEST_TOKENS[1],
        accounts[0],
        tickLO,
        1,
    )

    poolCopy2 = copy.deepcopy(pool)

    (_, _, amount, amountBurnt0_0, amountBurnt1_0) = poolCopy2.burnLimitOrder(
        TEST_TOKENS[1], accounts[0], tickLO, expandTo18Decimals(1) // 2
    )

    (_, _, amount, amountBurnt0_1, amountBurnt1_1) = poolCopy2.burnLimitOrder(
        TEST_TOKENS[1], accounts[0], tickLO, expandTo18Decimals(1) // 2
    )

    # Small rounding error
    assert correctAmountBurnt0 == amountBurnt0_0 + amountBurnt0_1 + 1
    assert correctAmountBurnt1 == amountBurnt1_0 + amountBurnt1_1

    tryExceptHandler(
        poolCopy2.burnLimitOrder,
        "LS",
        TEST_TOKENS[1],
        accounts[0],
        tickLO,
        1,
    )

    amountBurnt0Accum = 0
    amountBurnt1Accum = 0
    for i in range(4):
        (_, _, amount, amountBurnt0, amountBurnt1) = pool.burnLimitOrder(
            TEST_TOKENS[1], accounts[0], tickLO, expandTo18Decimals(1) // 4
        )
        amountBurnt0Accum += amountBurnt0
        amountBurnt1Accum += amountBurnt1

    # Small rounding error
    assert correctAmountBurnt0 == amountBurnt0Accum + 12
    assert correctAmountBurnt1 == amountBurnt1Accum + 2

    tryExceptHandler(
        poolCopy2.burnLimitOrder,
        "LS",
        TEST_TOKENS[1],
        accounts[0],
        tickLO,
        1,
    )


def test_burnPartiallySwapped_multipleSteps_oneForZero(
    initializedMediumPoolNoLO, accounts
):
    print("burn partially swapped positions in multiple steps - oneForZero")
    (
        pool,
        tickLO,
        priceLO,
        amountToSwap,
        amount1,
        liquidityPosition,
    ) = test_swap1For0_partialSwap(initializedMediumPoolNoLO, accounts)

    poolCopy = copy.deepcopy(pool)

    (_, _, amount, correctAmountBurnt0, correctAmountBurnt1) = poolCopy.burnLimitOrder(
        TEST_TOKENS[0], accounts[0], tickLO, expandTo18Decimals(1)
    )

    tryExceptHandler(
        poolCopy.burnLimitOrder,
        "LS",
        TEST_TOKENS[0],
        accounts[0],
        tickLO,
        1,
    )

    poolCopy2 = copy.deepcopy(pool)

    # Amount of swapped tokens that should get burnt regardless of newly minted orders on top
    (_, _, amount, amountBurnt0_0, amountBurnt1_0) = poolCopy2.burnLimitOrder(
        TEST_TOKENS[0], accounts[0], tickLO, expandTo18Decimals(1) // 2
    )

    (_, _, amount, amountBurnt0_1, amountBurnt1_1) = poolCopy2.burnLimitOrder(
        TEST_TOKENS[0], accounts[0], tickLO, expandTo18Decimals(1) // 2
    )

    # Small rounding error
    assert correctAmountBurnt0 == amountBurnt0_0 + amountBurnt0_1
    assert correctAmountBurnt1 == amountBurnt1_0 + amountBurnt1_1 + 1

    tryExceptHandler(
        poolCopy2.burnLimitOrder,
        "LS",
        TEST_TOKENS[0],
        accounts[0],
        tickLO,
        1,
    )

    amountBurnt0Accum = 0
    amountBurnt1Accum = 0
    for i in range(4):
        (_, _, amount, amountBurnt0, amountBurnt1) = pool.burnLimitOrder(
            TEST_TOKENS[0], accounts[0], tickLO, expandTo18Decimals(1) // 4
        )
        amountBurnt0Accum += amountBurnt0
        amountBurnt1Accum += amountBurnt1

    # Small rounding error
    assert correctAmountBurnt0 == amountBurnt0Accum + 2
    assert correctAmountBurnt1 == amountBurnt1Accum + 1

    tryExceptHandler(
        poolCopy2.burnLimitOrder,
        "LS",
        TEST_TOKENS[0],
        accounts[0],
        tickLO,
        1,
    )


def test_mintOnSwappedPosition_zeroForOne(initializedMediumPoolNoLO, accounts):
    print("mint on top of a swapped position/tick - zeroForOne")

    (
        pool,
        tickLO,
        priceLO,
        amountToSwap,
        amount1,
        liquidityPosition,
    ) = test_swap0For1_partialSwap(initializedMediumPoolNoLO, accounts)

    pos = pool.limitOrders[getLimitPositionKey(accounts[0], tickLO, False)]

    poolCopy = copy.deepcopy(pool)

    # Amount of swapped tokens that should get burnt regardless of newly minted orders on top
    (_, _, _, amount0_0, amount1_0) = poolCopy.burnLimitOrder(
        TEST_TOKENS[1], accounts[0], tickLO, liquidityPosition
    )

    # Mint on top of the previous position
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], tickLO, liquidityPosition * 1000)

    # Burn small amount to check if now the entire position gets swapped by the percentatge
    # swapped in the first swap
    assert pos.liquidity == liquidityPosition * (1 + 1000)

    (_, _, _, amount0, amount1) = pool.burnLimitOrder(
        TEST_TOKENS[1], accounts[0], tickLO, pos.liquidity
    )

    assert amount0_0 == amount0
    assert amount1 == amount1_0 + liquidityPosition * 1000


def test_mintOnSwappedPosition_oneForZero(initializedMediumPoolNoLO, accounts):
    print("mint on top of a swapped position/tick - oneForZero")

    (
        pool,
        tickLO,
        priceLO,
        amountToSwap,
        amount1,
        liquidityPosition,
    ) = test_swap1For0_partialSwap(initializedMediumPoolNoLO, accounts)

    pos = pool.limitOrders[getLimitPositionKey(accounts[0], tickLO, True)]
    poolCopy = copy.deepcopy(pool)

    # Amount of swapped tokens that should get burnt regardless of newly minted orders on top
    (_, _, _, amount0_0, amount1_0) = poolCopy.burnLimitOrder(
        TEST_TOKENS[0], accounts[0], tickLO, liquidityPosition
    )

    # Mint on top of the previous position
    pool.mintLimitOrder(TEST_TOKENS[0], accounts[0], tickLO, liquidityPosition * 1000)

    # Burn small amount to check if now the entire position gets swapped by the percentatge
    # swapped in the first swap
    assert pos.liquidity == liquidityPosition * (1 + 1000)

    (_, _, _, amount0, amount1) = pool.burnLimitOrder(
        TEST_TOKENS[0], accounts[0], tickLO, pos.liquidity
    )

    assert amount1_0 == amount1
    assert amount0 == amount0_0 + liquidityPosition * 1000


# Tests for LO on boundary/limit positions to check that LP's don't get too many tokens back when burning.
# In good price for user (bad for LP), they will get maximum the LP liquidity. Then LP wont get much.
# In bad price for user, user will give everything and not get much or anything. LO position should not
# have been swapped in that case and therefore the LP's position should remain the same, except accruing some fees.


def test_limitLO_badSwapPrice_zeroForOne(createPoolLow, accounts, ledger):
    pool, minTick, maxTick, _, _ = createPoolLow
    # Pool initialized at the far right - pool RO current tick > MAX LO tick
    pool.initialize(encodePriceSqrt(2**127, 1))
    tickSpacing = pool.tickSpacing

    [min, max] = [getMinTickLO(tickSpacing), getMaxTickLO(tickSpacing)]
    assert max < pool.slot0.tick

    iniBalance0LP = ledger.balanceOf(accounts[0], TEST_TOKENS[0])
    iniBalance1LP = ledger.balanceOf(accounts[0], TEST_TOKENS[1])

    pool.mintLimitOrder(
        TEST_TOKENS[0], accounts[0], TickMath.MAX_TICK_LO - 5, expandTo18Decimals(1)
    )

    assert pool.ticksLimitTokens0.__contains__(TickMath.MAX_TICK_LO - 5)
    # This should not happen since there should be a limit price, but checking behaviour anyway.
    (
        _,
        amount0,
        amount1,
        _,
        _,
        _,
    ) = swapExact1For0(pool, expandTo18Decimals(1), accounts[1], None)

    # All swapped for nothing
    assert amount0 == 0
    assert amount1 == expandTo18Decimals(1)

    # Position is not even burnt since the price is so high - percentatgeSwapped == 0
    assert pool.ticksLimitTokens0.__contains__(TickMath.MAX_TICK_LO - 5)
    assert (
        pool.ticksLimitTokens0[TickMath.MAX_TICK_LO - 5].amountPercSwappedInsideX128
        == 0
    )

    # Burn the position and check results
    (_, _, _, amount0, amount1) = pool.burnLimitOrder(
        TEST_TOKENS[0], accounts[0], TickMath.MAX_TICK_LO - 5, expandTo18Decimals(1)
    )

    (_, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[0], TickMath.MAX_TICK_LO - 5, MAX_UINT128, MAX_UINT128
    )

    # Final balance equal to the initial one plus fees (no actual swap has taken place)
    assert iniBalance0LP == ledger.balanceOf(accounts[0], TEST_TOKENS[0])
    assert (
        iniBalance1LP == ledger.balanceOf(accounts[0], TEST_TOKENS[1]) - 499999999999999
    )


def test_limitLO_badSwapPrice_OneForZero(createPoolLow, accounts, ledger):
    pool, minTick, maxTick, _, _ = createPoolLow
    # Pool initialized at the far right - pool RO current tick > MAX LO tick
    pool.initialize(encodePriceSqrt(1, 2**127))
    tickSpacing = pool.tickSpacing

    [min, max] = [getMinTickLO(tickSpacing), getMaxTickLO(tickSpacing)]
    assert min > pool.slot0.tick

    iniBalance0LP = ledger.balanceOf(accounts[0], TEST_TOKENS[0])
    iniBalance1LP = ledger.balanceOf(accounts[0], TEST_TOKENS[1])

    pool.mintLimitOrder(
        TEST_TOKENS[1], accounts[0], TickMath.MIN_TICK_LO + 5, expandTo18Decimals(1)
    )

    assert pool.ticksLimitTokens1.__contains__(TickMath.MIN_TICK_LO + 5)
    # This should not happen since there should be a limit price, but checking behaviour anyway.
    (
        _,
        amount0,
        amount1,
        _,
        _,
        _,
    ) = swapExact0For1(pool, expandTo18Decimals(1), accounts[1], None)

    # All swapped for nothing
    assert amount1 == 0
    assert amount0 == expandTo18Decimals(1)

    # Position is not even burnt since the price is so high - percentatgeSwapped == 0
    assert pool.ticksLimitTokens1.__contains__(TickMath.MIN_TICK_LO + 5)
    assert (
        pool.ticksLimitTokens1[TickMath.MIN_TICK_LO + 5].amountPercSwappedInsideX128
        == 0
    )

    # Burn the position and check results
    (_, _, _, amount0, amount1) = pool.burnLimitOrder(
        TEST_TOKENS[1], accounts[0], TickMath.MIN_TICK_LO + 5, expandTo18Decimals(1)
    )

    (_, _, amount0, amount1) = pool.collectLimitOrder(
        accounts[0], TEST_TOKENS[1], TickMath.MIN_TICK_LO + 5, MAX_UINT128, MAX_UINT128
    )

    # Final balance equal to the initial one plus fees (no actual swap has taken place)
    assert (
        iniBalance0LP == ledger.balanceOf(accounts[0], TEST_TOKENS[0]) - 499999999999999
    )
    assert iniBalance1LP == ledger.balanceOf(accounts[0], TEST_TOKENS[1])


# Precision test - AmountPercSwapped doesn't affect the swap amounts but we lose precision along the way
def test_precision_numberOfSwaps_sameAmount(createPoolLow, accounts, ledger):
    print("Check precision in tick.amountPercSwappedInsideX128")
    pool, minTick, maxTick, _, _ = createPoolLow
    pool.initialize(encodePriceSqrt(1, 1))

    pool.mintLimitOrder(
        TEST_TOKENS[1], accounts[0], pool.tickSpacing, expandTo18Decimals(10000)
    )
    tick = pool.ticksLimitTokens1[pool.tickSpacing]

    # Intial swap to get closet to the full swapped position
    swapExact0For1(pool, expandTo18Decimals(9800), accounts[1], None)

    numberOfSwaps = 10**4
    # Approach to the full position swap (taking into account some fees)
    amountPerSwap = int(
        (expandTo18Decimals(10000) - expandTo18Decimals(9800))
        // (numberOfSwaps + numberOfSwaps * 0.05)
    )
    # All swaps get the same price as long as the LO has liquidity
    amount0Prev = 1.904761904761905e16
    amount1Prev = -19057141902761161
    percSwappedPrev = 0
    # just the right amount before we cross the tick/position
    for i in range(numberOfSwaps+237):
        print("i", i)
        (
            _,
            amount0,
            amount1,
            _,
            _,
            _,
        ) = swapExact0For1(pool, amountPerSwap, accounts[1], None)
        # AmountPercSwapped doesn't affect the swap amounts
        assert amount0Prev == amount0
        assert amount1Prev == amount1
        if i == 0:
            # First swap sets the amountPercSwappedInsideX128
            assert tick.amountPercSwappedInsideX128 - percSwappedPrev == 333644089714382253081950632032915180131
        else:
            print("tick.amountPercSwappedInsideX128", tick.amountPercSwappedInsideX128)
            print("diff", tick.amountPercSwappedInsideX128 - percSwappedPrev )
            #assert tick.amountPercSwappedInsideX128 - percSwappedPrev == 648480935341976477991928071539899
            # Since amounts are the same, liquidity left keeps decreasing, which means in each swap the percentatge swap increased is constant.
            # In some swaps the precision is a bit off due to rounding - around 1/3 fulfill the first one, 2/3rds the second one. 
            # But precision doesnt keep decreasing, it seems like a rounding on the compute Math. 
            # This is only because the swaps are the same I believe. If they were different amounts we would start losing precision.
            assert tick.amountPercSwappedInsideX128 - percSwappedPrev == 648480935341976477991928071539899 or tick.amountPercSwappedInsideX128 - percSwappedPrev == 648480935341976477991928071539900
        print(
            "tick.liquidityLeft",
            tick.liquidityLeft,
        )
        percSwappedPrev = tick.amountPercSwappedInsideX128

    # Backup order to make sure we can cross the previous order succesfully.
    pool.mintLimitOrder(TEST_TOKENS[1], accounts[0], 0, expandTo18Decimals(100))
    swapExact0For1(pool, expandTo18Decimals(100), accounts[1], None)
    print(pool.ticksLimitTokens1)

    assert not pool.ticksLimitTokens1.__contains__(pool.tickSpacing)


# Precision test - AmountPercSwapped doesn't affect the swap amounts but we lose precision along the way
def test_precision_numberOfSwaps_diffAmount(createPoolLow, accounts, ledger):
    print("Check precision in tick.amountPercSwappedInsideX128")
    pool, minTick, maxTick, _, _ = createPoolLow
    pool.initialize(encodePriceSqrt(1, 1))
    pool.slot0.tick = -1

    pool.mintLimitOrder(
        TEST_TOKENS[1], accounts[0], 0, expandTo18Decimals(10000)
    )
    tick = pool.ticksLimitTokens1[0]

    print("tick.liquidityLeft", tick.liquidityLeft)
    counter = 0
    percSwappedPrev = 0
    precList = [0]

    while pool.ticksLimitTokens1[0].liquidityLeft > 1000:
        print("tick", tick)
        amount = random.randint(1000,pool.ticksLimitTokens1[0].liquidityLeft)
        liqLeftBeforeSwap = pool.ticksLimitTokens1[0].liquidityLeft
        (
            _,
            amount0,
            amount1,
            sqrtPriceX96,
            liquidity,
            tick,
        ) =swapExact0For1(
            pool,
            amount,
            accounts[1],
            None,
        )

        print("tick", pool.ticksLimitTokens1[0])

        perc = (FixedPoint128_Q128 * abs(amount1)) // liqLeftBeforeSwap
        print("perc", perc)
        print("diff", pool.ticksLimitTokens1[0].amountPercSwappedInsideX128 - percSwappedPrev)
        print("tick.liquidityLeft", pool.ticksLimitTokens1[0].liquidityLeft)

        # Manual calculation of swapped perc done when position is burnt (if it was minted bnefore this current swap)
        percCalcul = mulDivRoundingUp(
            toUint256(
                pool.ticksLimitTokens1[0].amountPercSwappedInsideX128 - percSwappedPrev
            ),
            FixedPoint128_Q128,
            toUint256(FixedPoint128_Q128 - percSwappedPrev),
        )
        print("percCalcul", percCalcul)
        #assert percCalcul == perc
        precisionError = abs(percCalcul - perc)
        print("Precision error", precisionError)
        # Error doesn't necessarily increase in each swap (some might be lower) but in general the trend is that it keeps increasing
        precList.append(precisionError)

        percSwappedPrev = pool.ticksLimitTokens1[0].amountPercSwappedInsideX128
        counter += 1
        print("counter", counter)

    print("Precision error list", precList)
    assert False

# Precision test - it might be that the closer the amountPercSwappedInsideX128 is to 1 the more precision we lose per swap.
# However, in this test it seems that we lose some precision but not relevant, extremely difficult to hit (so many decimals).
# Also, the more we approach (1-...) being close to zero, the smaller liquidity left is, so the precision loss is not so huge.
def test_precision_closeTo1(createPoolLow, accounts):
    print("Check precision in tick.amountPercSwappedInsideX128")
    pool, minTick, maxTick, _, _ = createPoolLow
    pool.initialize(encodePriceSqrt(1, 1))

    # Fake pool to -1 so we can swap asset 1 to 1 (ease calculations)
    pool.slot0.tick = -1

    pool.mintLimitOrder(
        TEST_TOKENS[1], accounts[0], 0, expandTo18Decimals(10000)
    )
    # This swap changes the amountPercSwappedInsideX128
    tick = pool.ticksLimitTokens1[0]
    assert tick.amountPercSwappedInsideX128 == 0
    print("percSwapped0to1: ", tick.amountPercSwappedInsideX128 / FixedPoint128_Q128)
    print("percSwappedAbs: ", tick.amountPercSwappedInsideX128)
    print("tick: ", tick)
    swapExact0For1(pool, 100, accounts[1], None)
    print("percSwapped0to1: ", tick.amountPercSwappedInsideX128 / FixedPoint128_Q128)
    print("percSwappedAbs: ", tick.amountPercSwappedInsideX128)
    print("tick: ", tick)
    assert tick.amountPercSwappedInsideX128 > 0

    print("--SWAP2--")
    # This swap still changes the amountPercSwappedInsideX128
    swapExact0For1(pool, 10, accounts[1], None)
    print("percSwapped0to1: ", tick.amountPercSwappedInsideX128 / FixedPoint128_Q128)
    print("percSwappedAbs: ", tick.amountPercSwappedInsideX128)
    print("tick: ", tick)
    assert tick.amountPercSwappedInsideX128 > 0
    previousPerc = tick.amountPercSwappedInsideX128

    print("--SWAP3--")
    # Swap to get closet to the full swapped position (minus fees)
    liqLeft = tick.liquidityLeft # == expandTo18Decimals(10000) - 100 - 10 - fees
    print("liqLeft: ", liqLeft)
    # This amount leaves last position with liquidityLeft == 1
    maxAmountToSwap = mulDiv(
            liqLeft, SwapMath.ONE_IN_PIPS, SwapMath.ONE_IN_PIPS - pool.fee
        )

    swapExact0For1(
        pool,
        maxAmountToSwap - 5,
        accounts[1],
        None,
    )
    assert tick.liquidityLeft == 6
    assert tick.amountPercSwappedInsideX128 > 0
    assert tick.amountPercSwappedInsideX128 > previousPerc
    previousPerc = tick.amountPercSwappedInsideX128
    print(tick)

    # Check tokens that would be obtained if position were to be burnt
    (_, _, amount, amountIniBurnt0, amountIniBurnt1) = copy.deepcopy(pool).burnLimitOrder(
        TEST_TOKENS[1], accounts[0], 0, expandTo18Decimals(10000)
    )    

    # Mint another position
    pool.mintLimitOrder(
        TEST_TOKENS[1], accounts[2], 0, 14
    )
    assert tick.liquidityLeft == 20

    # Swap 11 tokens pool which ends up being 10 tokens out after fees
    swapExact0For1(
        pool,
        11,
        accounts[1],
        None,
    )    
    print(tick)
    assert tick.liquidityLeft == 10
    assert tick.amountPercSwappedInsideX128 > 0
    assert tick.amountPercSwappedInsideX128 > previousPerc
    print("previousPerc: ", previousPerc)
    print("tick.amountPercSwappedInsideX128", tick.amountPercSwappedInsideX128)
    print("substraction", tick.amountPercSwappedInsideX128- previousPerc)

    # Swapped
    swapPerc = 10 / 20
    # Burn amounts
    amountBurntNewPos = int(swapPerc * 14)
    amountBurntOldPos = int(swapPerc * 6)
    print("amountBurntNewPos", amountBurntNewPos)
    print("amountBurntOldPos", amountBurntOldPos)

    (_, _, amount, amountBurnt0, amountBurnt1) = pool.burnLimitOrder(
        TEST_TOKENS[1], accounts[2], 0, 14
    )
    assert amountBurnt1 == amountBurntNewPos
    assert amountBurnt0 == amountBurntNewPos # ratio 1:1
    print(tick)
    print(pool.limitOrders)
    (_, _, amount, amountBurnt0, amountBurnt1) = pool.burnLimitOrder(
        TEST_TOKENS[1], accounts[0], 0, expandTo18Decimals(10000)
    )
    print(amountBurnt1)
    assert amountBurnt1 == amountIniBurnt1 - 3 
    assert amountBurnt0 == amountIniBurnt0 + 3 # ratio 1:1



# # Trying random LO positions on top of RO and check behaviour. Also check that pool RO pool behaves the same
# # if there are LO that are not used as if there were are none.
# @given(
#     st_isToken0=strategy("bool"),
#     # Using reasonable ticks
#     st_tick=strategy("int128", min_value=-1000, max_value=1000),
#     st_mintAmount=strategy("uint128", min_value=100, max_value=expandTo18Decimals(1)),
#     # By default the max amount of elements is 8 === number of swaps. Making swaps of a relevant size
#     st_swapAmounts=strategy(
#         "uint128[]", min_value=1000, max_value=expandTo18Decimals(1)
#     ),
# )
# def test_randomLO_onRO_zeroForOne(st_isToken0, st_swapAmounts, st_tick, st_mintAmount):
#     print(
#         "Trying random LO position on top of RO and random swaps in the zeroForOne direction"
#     )

#     # Create accounts, ledger and pool because there is issues when using fixtures
#     account0 = [
#         "ALICE",
#         TEST_TOKENS,
#         [MAX_INT256 // 100, MAX_INT256 // 100 // 100],
#     ]  # LP0 - backup liquidity
#     account1 = ["BOB", TEST_TOKENS, [MAX_INT256 // 100, MAX_INT256 // 100]]  # LP1
#     account2 = [
#         "CHARLIE",
#         TEST_TOKENS,
#         [MAX_INT256 // 100, MAX_INT256 // 100],
#     ]  # Swapper

#     ledger = Ledger([account0, account1, account2])
#     accounts = list(ledger.accounts.keys())

#     pool, minTick, maxTick, _, _ = createPool(
#         FeeAmount.MEDIUM, TICK_SPACINGS[FeeAmount.MEDIUM], ledger
#     )

#     pool.initialize(encodePriceSqrt(1, 1))

#     # Add some RO Liquidity as a base
#     pool.mint(accounts[0], minTick, maxTick, expandTo18Decimals(100))

#     token = TEST_TOKENS[0] if st_isToken0 else TEST_TOKENS[1]
#     iniBalance0LOLP = ledger.balanceOf(accounts[1], TEST_TOKENS[0])
#     iniBalance1LOLP = ledger.balanceOf(accounts[1], TEST_TOKENS[1])

#     # Get close stick at correct tickSpacing and mint LO
#     LOtickSpaced = st_tick - st_tick % pool.tickSpacing

#     # Price in which the LO will be taken
#     LOPrice = TickMath.getPriceAtTick(LOtickSpaced)
#     LOatSqrtPrice = TickMath.getSqrtRatioAtTick(LOtickSpaced - 1)
#     LOSqrtPrice = TickMath.getSqrtRatioAtTick(LOtickSpaced)

#     # Figure out if LO should be used
#     if st_isToken0 == True:
#         limitOrderUsed = False
#         ROtickCrossedExactly = False
#     else:
#         (finalSqrtPriceX96, amountIn, amountOut, feeAmount,) = SwapMath.computeSwapStep(
#             pool.slot0.sqrtPriceX96,  # tick 0
#             LOatSqrtPrice,
#             pool.liquidity,
#             sum(st_swapAmounts),  # All swaps bundled
#             pool.fee,
#         )

#         if LOatSqrtPrice == finalSqrtPriceX96:
#             ROtickCrossedExactly = True
#         else:
#             ROtickCrossedExactly = False

#         # Due to the nature of zeroForOne, in multiple swaps, if one of them moves the pool a bit
#         # then the tick becomes -1 which makes it use the LO.
#         if finalSqrtPriceX96 < LOSqrtPrice or LOtickSpaced > pool.slot0.tick:
#             # Reached limit order
#             limitOrderUsed = True
#         else:
#             limitOrderUsed = False

#         # Get if LO tick should be crossed
#         (_, _, _, tickCrossed,) = SwapMath.computeLimitSwapStep(
#             LOPrice,
#             st_mintAmount,
#             sum(st_swapAmounts),
#             pool.fee,
#             True,  # zeroForOne
#         )

#     # Mint Limit Order on top
#     pool.mintLimitOrder(token, accounts[1], LOtickSpaced, st_mintAmount)

#     # Check the st_mintAmount is transferred correctly
#     if st_isToken0:
#         assert iniBalance0LOLP - st_mintAmount == ledger.balanceOf(
#             accounts[1], TEST_TOKENS[0]
#         )
#         assert iniBalance1LOLP == ledger.balanceOf(accounts[1], TEST_TOKENS[1])
#     else:
#         assert iniBalance0LOLP == ledger.balanceOf(accounts[1], TEST_TOKENS[0])
#         assert iniBalance1LOLP - st_mintAmount == ledger.balanceOf(
#             accounts[1], TEST_TOKENS[1]
#         )

#     ticksLimit = pool.ticksLimitTokens0 if st_isToken0 else pool.ticksLimitTokens1
#     tick = ticksLimit[LOtickSpaced]
#     position = pool.limitOrders[
#         getLimitPositionKey(accounts[1], LOtickSpaced, st_isToken0)
#     ]
#     iniPosition = copy.deepcopy(position)

#     for swapAmount in st_swapAmounts:
#         swapExact0For1(pool, swapAmount, accounts[2], None)

#     if not limitOrderUsed:
#         assert tick.liquidityGross == st_mintAmount
#         assert tick.liquidityLeft == st_mintAmount
#         assert tick.amountPercSwappedInsideX128 == 0
#         assert tick.feeGrowthInsideX128 == 0
#         # Nothing has changed in the position
#         assert position == iniPosition

#         balanceBeforeBurn0LOLP = ledger.balanceOf(accounts[1], TEST_TOKENS[0])
#         balanceBeforeBurn1LOLP = ledger.balanceOf(accounts[1], TEST_TOKENS[1])
#         # Burn LO LP position
#         pool.burnLimitOrder(token, accounts[1], LOtickSpaced, st_mintAmount)
#         # Burn does not change the balances
#         assert balanceBeforeBurn0LOLP == ledger.balanceOf(accounts[1], TEST_TOKENS[0])
#         assert balanceBeforeBurn1LOLP == ledger.balanceOf(accounts[1], TEST_TOKENS[1])
#         pool.collectLimitOrder(
#             accounts[1], token, LOtickSpaced, MAX_UINT128, MAX_UINT128
#         )
#         finalBalance0LOLP = ledger.balanceOf(accounts[1], TEST_TOKENS[0])
#         finalBalance1LOLP = ledger.balanceOf(accounts[1], TEST_TOKENS[1])
#         # Assert that final balance == initial value since there's been no swap on that tick/position
#         assert finalBalance0LOLP == iniBalance0LOLP
#         assert finalBalance1LOLP == iniBalance1LOLP
#     else:
#         # Assert that the LO has been partially or fully used
#         if LOtickSpaced > 0:  # 0 == intial tick
#             if pool.slot0.tick != 0:  # != initial tick
#                 assertLimitPositionIsBurnt(
#                     pool.limitOrders, accounts[1], LOtickSpaced, st_isToken0
#                 )
#             else:
#                 # Tick/position partially swapped or fully swapped. It can be that it crossed the tick at the exact same
#                 # time that the swap is complete.
#                 if tickCrossed:
#                     assertLimitPositionIsBurnt(
#                         pool.limitOrders, accounts[1], LOtickSpaced, st_isToken0
#                     )
#                 else:
#                     assert tick.amountPercSwappedInsideX128 > 0
#                     assertLimitPositionExists(
#                         pool.limitOrders, accounts[1], LOtickSpaced, st_isToken0
#                     )
#         # RO are swapped first
#         else:
#             if pool.slot0.tick < LOtickSpaced - 1:
#                 # Position swapped if pool reaches tick after the tick where LO will be used
#                 assertLimitPositionIsBurnt(
#                     pool.limitOrders, accounts[1], LOtickSpaced, st_isToken0
#                 )
#             elif pool.slot0.tick == LOtickSpaced - 1:
#                 # Tick/position most likely partially swapped (could be fully swapped too
#                 # but the amounts would need to be extremely exact. Could also be not swapped but
#                 # then we should not be in this case)
#                 if ROtickCrossedExactly:
#                     assert tick.amountPercSwappedInsideX128 > 0
#                     assertLimitPositionExists(
#                         pool.limitOrders, accounts[1], LOtickSpaced, st_isToken0
#                     )
#                 else:
#                     # Could be any scenario (partially swapped and fully-swapped). Almost impossible
#                     # to predict without doing all the math - we skip the check for now.
#                     assert True
#             else:
#                 # Shoul not reach here anyway bc it's certain that LO has not been used.
#                 assert False, "Should never reach this"


# @given(
#     st_isToken0=strategy("bool"),
#     # Using reasonable ticks
#     st_tick=strategy("int128", min_value=-1000, max_value=1000),
#     st_mintAmount=strategy("uint128", min_value=100, max_value=expandTo18Decimals(1)),
#     # By default the max amount of elements is 8 === number of swaps. Making swaps of a relevant size
#     st_swapAmounts=strategy(
#         "uint128[]", min_value=1000, max_value=expandTo18Decimals(1)
#     ),
# )
# def test_randomLO_onRO_oneForZero(st_isToken0, st_swapAmounts, st_tick, st_mintAmount):

#     print(
#         "Trying random LO position on top of RO and random swaps in the OneForZero direction"
#     )

#     # Create accounts, ledger and pool because there is issues when using fixtures
#     account0 = [
#         "ALICE",
#         TEST_TOKENS,
#         [MAX_INT256 // 100, MAX_INT256 // 100 // 100],
#     ]  # LP0 - backup liquidity
#     account1 = ["BOB", TEST_TOKENS, [MAX_INT256 // 100, MAX_INT256 // 100]]  # LP1
#     account2 = [
#         "CHARLIE",
#         TEST_TOKENS,
#         [MAX_INT256 // 100, MAX_INT256 // 100],
#     ]  # Swapper

#     ledger = Ledger([account0, account1, account2])
#     accounts = list(ledger.accounts.keys())

#     pool, minTick, maxTick, _, _ = createPool(
#         FeeAmount.MEDIUM, TICK_SPACINGS[FeeAmount.MEDIUM], ledger
#     )

#     pool.initialize(encodePriceSqrt(1, 1))

#     # Add some RO Liquidity as a base
#     pool.mint(accounts[0], minTick, maxTick, expandTo18Decimals(100))

#     token = TEST_TOKENS[0] if st_isToken0 else TEST_TOKENS[1]
#     iniBalance0LOLP = ledger.balanceOf(accounts[1], TEST_TOKENS[0])
#     iniBalance1LOLP = ledger.balanceOf(accounts[1], TEST_TOKENS[1])

#     # Get close stick at correct tickSpacing and mint LO
#     LOtickSpaced = st_tick - st_tick % pool.tickSpacing

#     # Price in which the LO will be taken
#     LOPrice = TickMath.getPriceAtTick(LOtickSpaced)
#     LOSqrtPrice = TickMath.getSqrtRatioAtTick(LOtickSpaced)

#     # Figure out if LO should be used
#     if st_isToken0 == False:
#         limitOrderUsed = False
#         ROtickCrossedExactly = False
#     else:
#         (finalSqrtPriceX96, amountIn, amountOut, feeAmount,) = SwapMath.computeSwapStep(
#             pool.slot0.sqrtPriceX96,  # tick 0
#             LOSqrtPrice,
#             pool.liquidity,
#             sum(st_swapAmounts),  # All swaps bundled
#             pool.fee,
#         )

#         if LOSqrtPrice == finalSqrtPriceX96:
#             ROtickCrossedExactly = True
#         else:
#             ROtickCrossedExactly = False

#         # Due to the nature of zeroForOne, in multiple swaps, if one of them moves the pool a bit
#         # then the tick becomes -1 which makes it use the LO.
#         if finalSqrtPriceX96 >= LOSqrtPrice or LOtickSpaced <= pool.slot0.tick:
#             # Reached limit order
#             limitOrderUsed = True
#         else:
#             limitOrderUsed = False

#         # Get if LO tick should be crossed
#         (_, _, _, tickCrossed,) = SwapMath.computeLimitSwapStep(
#             LOPrice,
#             st_mintAmount,
#             sum(st_swapAmounts),
#             pool.fee,
#             True,  # zeroForOne
#         )

#     # Mint Limit Order on top
#     pool.mintLimitOrder(token, accounts[1], LOtickSpaced, st_mintAmount)

#     # Check the st_mintAmount is transferred correctly
#     if st_isToken0:
#         assert iniBalance0LOLP - st_mintAmount == ledger.balanceOf(
#             accounts[1], TEST_TOKENS[0]
#         )
#         assert iniBalance1LOLP == ledger.balanceOf(accounts[1], TEST_TOKENS[1])
#     else:
#         assert iniBalance0LOLP == ledger.balanceOf(accounts[1], TEST_TOKENS[0])
#         assert iniBalance1LOLP - st_mintAmount == ledger.balanceOf(
#             accounts[1], TEST_TOKENS[1]
#         )

#     ticksLimit = pool.ticksLimitTokens0 if st_isToken0 else pool.ticksLimitTokens1
#     tick = ticksLimit[LOtickSpaced]
#     position = pool.limitOrders[
#         getLimitPositionKey(accounts[1], LOtickSpaced, st_isToken0)
#     ]
#     iniPosition = copy.deepcopy(position)

#     for swapAmount in st_swapAmounts:
#         swapExact1For0(pool, swapAmount, accounts[2], None)

#     if not limitOrderUsed:
#         assert tick.liquidityGross == st_mintAmount
#         assert tick.liquidityLeft == st_mintAmount
#         assert tick.amountPercSwappedInsideX128 == 0
#         assert tick.feeGrowthInsideX128 == 0
#         # Nothing has changed in the position
#         assert position == iniPosition

#         balanceBeforeBurn0LOLP = ledger.balanceOf(accounts[1], TEST_TOKENS[0])
#         balanceBeforeBurn1LOLP = ledger.balanceOf(accounts[1], TEST_TOKENS[1])
#         # Burn LO LP position
#         pool.burnLimitOrder(token, accounts[1], LOtickSpaced, st_mintAmount)
#         # Burn does not change the balances
#         assert balanceBeforeBurn0LOLP == ledger.balanceOf(accounts[1], TEST_TOKENS[0])
#         assert balanceBeforeBurn1LOLP == ledger.balanceOf(accounts[1], TEST_TOKENS[1])
#         pool.collectLimitOrder(
#             accounts[1], token, LOtickSpaced, MAX_UINT128, MAX_UINT128
#         )
#         finalBalance0LOLP = ledger.balanceOf(accounts[1], TEST_TOKENS[0])
#         finalBalance1LOLP = ledger.balanceOf(accounts[1], TEST_TOKENS[1])
#         # Assert that final balance == initial value since there's been no swap on that tick/position
#         assert finalBalance0LOLP == iniBalance0LOLP
#         assert finalBalance1LOLP == iniBalance1LOLP
#     else:
#         # Assert that the LO has been partially or fully used
#         if LOtickSpaced <= 0:  # 0 == intial tick
#             if pool.slot0.tick != 0:  # != initial tick
#                 assertLimitPositionIsBurnt(
#                     pool.limitOrders, accounts[1], LOtickSpaced, st_isToken0
#                 )
#             else:
#                 # Tick/position partially swapped or fully swapped. It can be that it crossed the tick at the exact same
#                 # time that the swap is complete.
#                 if tickCrossed:
#                     assertLimitPositionIsBurnt(
#                         pool.limitOrders, accounts[1], LOtickSpaced, st_isToken0
#                     )
#                 else:
#                     assert tick.amountPercSwappedInsideX128 > 0
#                     assertLimitPositionExists(
#                         pool.limitOrders, accounts[1], LOtickSpaced, st_isToken0
#                     )
#         # RO are swapped first
#         else:
#             if pool.slot0.tick > LOtickSpaced:
#                 # Position swapped if pool reaches tick after the tick where LO will be used
#                 assertLimitPositionIsBurnt(
#                     pool.limitOrders, accounts[1], LOtickSpaced, st_isToken0
#                 )
#             elif pool.slot0.tick == LOtickSpaced:
#                 # Tick/position most likely partially swapped (could be fully swapped too
#                 # but the amounts would need to be extremely exact. Could also be not swapped but
#                 # then we should not be in this case)
#                 if not ROtickCrossedExactly:
#                     assert tick.amountPercSwappedInsideX128 > 0
#                     assertLimitPositionExists(
#                         pool.limitOrders, accounts[1], LOtickSpaced, st_isToken0
#                     )
#                 else:
#                     # Could be any scenario (partially swapped and fully-swapped). Almost impossible
#                     # to predict without doing all the math - we skip the check for now.
#                     assert True
#             else:
#                 # Shoul not reach here anyway bc it's certain that LO has not been used.
#                 assert False, "Should never reach this"


###### LO Testing utilities ######

# Check partially swapped single limit order
def check_limitOrderSwap_oneTick_exactIn(
    pool,
    position,
    tickLO,
    amountToSwap,
    iniLiquidityTick,
    amountSwappedIn,
    amountSwappedOut,
    zeroForOne,
    one_in_pips,
    priceLO,
):
    assert amountSwappedIn == amountToSwap

    amountRemainingLessFee = mulDiv(
        (amountToSwap),
        (one_in_pips - pool.fee),
        one_in_pips,
    )

    if zeroForOne:
        amountOut = -SqrtPriceMath.calculateAmount1LO(amountRemainingLessFee, priceLO)
        ticksLimitTokens = pool.ticksLimitTokens1
    else:
        amountOut = -SqrtPriceMath.calculateAmount0LO(amountRemainingLessFee, priceLO)
        ticksLimitTokens = pool.ticksLimitTokens0
    assert amountSwappedOut == amountOut

    # Check LO position and tick
    assert pool.limitOrders[position].liquidity == iniLiquidityTick
    assert ticksLimitTokens[tickLO].liquidityLeft == iniLiquidityTick - abs(
        amountSwappedOut
    )
    assert ticksLimitTokens[tickLO].liquidityGross == iniLiquidityTick


# Fully burn a partially swapped position
def check_burn_limitOrderSwap_oneTick_exactIn(
    pool,
    owner,
    tickLO,
    amountToBurn,
    amountSwapped,
    zeroForOne,
    priceLO,
    tickToBeCleared,
):
    token = TEST_TOKENS[1] if zeroForOne else TEST_TOKENS[0]

    (_, _, amount, amountBurnt0, amountBurnt1) = pool.burnLimitOrder(
        token, owner, tickLO, amountToBurn
    )
    assert amount == amountToBurn

    if zeroForOne:
        assert amountBurnt0 == SqrtPriceMath.calculateAmount0LO(
            abs(amountSwapped), priceLO
        )
        if tickToBeCleared:
            assert not pool.ticksLimitTokens1.__contains__(tickLO)

    else:
        assert amountBurnt1 == SqrtPriceMath.calculateAmount1LO(
            abs(amountSwapped), priceLO
        )
        if tickToBeCleared:
            assert not pool.ticksLimitTokens0.__contains__(tickLO)

    # Check LO position and tick
    assert (
        pool.limitOrders[getLimitPositionKey(owner, tickLO, not zeroForOne)].liquidity
        == 0
    )

    # Collect position
    (_, _, amount0, amount1) = pool.collectLimitOrder(
        owner, token, tickLO, MAX_UINT128, MAX_UINT128
    )

    # Check that amount calculated in burn against the amount collected - fees accrued
    if zeroForOne:
        assert amountBurnt1 == amount1
        if amountSwapped != 0:
            # Fees accrued in token0
            assert amountBurnt0 < amount0
        else:
            assert amountBurnt0 == amount0
    else:
        assert amountBurnt0 == amount0
        if amountSwapped != 0:
            # Fees accrued in token1
            assert amountBurnt1 < amount1
        else:
            assert amountBurnt1 == amount1

    # No liquidity left and all tokensOwed collected - check that the position is cleared
    assertLimitPositionIsBurnt(pool.limitOrders, owner, tickLO, not zeroForOne)
