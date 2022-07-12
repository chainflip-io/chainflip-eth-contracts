from utilities import *
from UniswapPool import *
from Factory import *

import pytest


@pytest.fixture
def accounts():
    # Fund them with infinite tokens
    account0 = Account("ALICE", TEST_TOKENS, [MAX_INT256, MAX_INT256])
    account1 = Account("BOB", TEST_TOKENS, [MAX_INT256, MAX_INT256])
    return account0, account1


def createPool(feeAmount):
    factory = Factory()
    feeAmount = feeAmount
    tickSpacing = TICK_SPACINGS[feeAmount]
    pool = factory.createPool(TEST_TOKENS[0], TEST_TOKENS[1], feeAmount)
    minTick = getMinTick(tickSpacing)
    maxTick = getMaxTick(tickSpacing)
    return pool, factory, minTick, maxTick, feeAmount, tickSpacing


@pytest.fixture
def createPoolMedium():
    return createPool(FeeAmount.MEDIUM)


@pytest.fixture
def createPoolLow():
    return createPool(FeeAmount.LOW)


@pytest.fixture
def initializedPool(createPoolMedium, accounts):
    pool, _, minTick, maxTick, _, _ = createPoolMedium
    pool.initialize(encodePriceSqrt(1, 10))
    pool.mint(accounts[0], minTick, maxTick, 3161)
    return createPoolMedium


def test_constructor(createPoolMedium):
    print("constructor initializes immutables")
    pool, factory, _, _, _, _ = createPoolMedium
    assert factory.getPool[0] == [TEST_TOKENS[0], TEST_TOKENS[1], FeeAmount.MEDIUM]
    assert pool.token0 == TEST_TOKENS[0]
    assert pool.token1 == TEST_TOKENS[1]


# Initialize
def test_fails_alreadyInitialized(createPoolMedium):
    print("fails if already initialized")
    pool, _, _, _, _, _ = createPoolMedium
    pool.initialize(encodePriceSqrt(1, 1))
    tryExceptHandler(pool.initialize, "AI", encodePriceSqrt(1, 1))


def test_fails_lowStartingPrice(createPoolMedium):
    pool, _, _, _, _, _ = createPoolMedium
    print("fails if already initialized")
    tryExceptHandler(pool.initialize, "R", 1)
    tryExceptHandler(pool.initialize, "R", TickMath.MIN_SQRT_RATIO - 1)


def test_fails_highStartingPrice(createPoolMedium):
    print("fails if already initialized")
    pool, _, _, _, _, _ = createPoolMedium
    tryExceptHandler(pool.initialize, "R", TickMath.MAX_SQRT_RATIO)
    tryExceptHandler(pool.initialize, "R", MAX_UINT160)


def test_initialize_MIN_SQRT_RATIO(createPoolMedium):
    print("can be initialized at MIN_SQRT_RATIO")
    pool, _, _, _, _, _ = createPoolMedium
    pool.initialize(TickMath.MIN_SQRT_RATIO)
    assert pool.slot0.tick == getMinTick(1)


def test_initialize_MAX_SQRT_RATIO_minusOne(createPoolMedium):
    print("can be initialized at MAX_SQRT_RATIO - 1")
    pool, _, _, _, _, _ = createPoolMedium
    pool.initialize(TickMath.MAX_SQRT_RATIO - 1)
    assert pool.slot0.tick == getMaxTick(1) - 1


def test_setInitialVariables(createPoolMedium):
    print("sets initial variables")
    pool, _, _, _, _, _ = createPoolMedium
    price = encodePriceSqrt(1, 2)
    pool.initialize(price)

    assert pool.slot0.sqrtPriceX96 == price
    assert pool.slot0.tick == -6932


# Mint


def test_initialize_10to1(createPoolMedium, accounts):
    pool, _, minTick, maxTick, _, _ = createPoolMedium
    pool.initialize(encodePriceSqrt(1, 10))
    pool.mint(accounts[0], minTick, maxTick, 3161)


def test_fails_tickLower_gtTickUpper(initializedPool, accounts):
    print("fails if tickLower greater than tickUpper")
    pool, _, _, _, _, _ = initializedPool
    tryExceptHandler(pool.mint, "TLU", accounts[0], 1, 0, 1)


def test_fails_tickLower_ltMinTick(initializedPool, accounts):
    print("fails if tickLower less than min Tick")
    pool, _, _, _, _, _ = initializedPool
    tryExceptHandler(pool.mint, "TLM", accounts[0], -887273, 0, 1)


def test_fails_tickUpper_gtMaxTick(initializedPool, accounts):
    print("fails if tickUpper greater than max Tick")
    pool, _, _, _, _, _ = initializedPool
    tryExceptHandler(pool.mint, "TUM", accounts[0], 0, 887273, 1)


def test_fails_amountGtMax(initializedPool, accounts):
    print("fails if amount exceeds the max")
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    maxLiquidityGross = pool.maxLiquidityPerTick
    tryExceptHandler(
        pool.mint, "LO", accounts[0], minTick + tickSpacing, maxTick - tickSpacing, maxLiquidityGross + 1
    )
    pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, maxLiquidityGross)


def test_fails_totalAmountatTick_gtMAX(initializedPool, accounts):
    print("fails if total amount at tick exceeds the max")
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 1000)

    maxLiquidityGross = pool.maxLiquidityPerTick
    tryExceptHandler(
        pool.mint,
        "LO",
        accounts[0],
        minTick + tickSpacing,
        maxTick - tickSpacing,
        maxLiquidityGross - 1000 + 1,
    )
    tryExceptHandler(
        pool.mint,
        "LO",
        accounts[0],
        minTick + tickSpacing * 2,
        maxTick - tickSpacing,
        maxLiquidityGross - 1000 + 1,
    )
    tryExceptHandler(
        pool.mint,
        "LO",
        accounts[0],
        minTick + tickSpacing,
        maxTick - tickSpacing * 2,
        maxLiquidityGross - 1000 + 1,
    )
    pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, maxLiquidityGross - 1000)


def test_fails_zeroAmount(initializedPool, accounts):
    print("fails if amount is zero")
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    tryExceptHandler(pool.mint, "", accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 0)


# Success cases


def test_initial_balances(initializedPool):
    print("fails if amount is zero")
    pool, _, _, _, _, _ = initializedPool
    assert pool.balances[pool.token0] == 9996
    assert pool.balances[pool.token1] == 1000


def test_initialTick(initializedPool):
    print("fails if amount is zero")
    pool, _, _, _, _, _ = initializedPool
    assert pool.slot0.tick == -23028


# Above current tick
def test_transferToken0_only(initializedPool, accounts):
    print("transferToken0 only")
    pool, _, _, _, _, _ = initializedPool
    (amount0, amount1) = pool.mint(accounts[0], -22980, 0, 10000)
    assert amount0 != 0
    assert amount1 == 0
    assert pool.balances[pool.token0] == 9996 + 21549
    assert pool.balances[pool.token1] == 1000


def test_maxTick_maxLeverage(initializedPool, accounts):
    print("max tick with max leverage")
    pool, _, _, maxTick, _, tickSpacing = initializedPool
    pool.mint(accounts[0], maxTick - tickSpacing, maxTick, 2**102)
    assert pool.balances[pool.token0] == 9996 + 828011525
    assert pool.balances[pool.token1] == 1000


def test_maxTick(initializedPool, accounts):
    print("works for max tick")
    pool, _, _, maxTick, _, _ = initializedPool
    pool.mint(accounts[0], -22980, maxTick, 10000)
    assert pool.balances[pool.token0] == 9996 + 31549
    assert pool.balances[pool.token1] == 1000


def test_remove_aboveCurrentPrice(initializedPool, accounts):
    print("removing works")
    pool, _, _, _, _, _ = initializedPool
    pool.mint(accounts[0], -240, 0, 10000)
    pool.burn(accounts[0], -240, 0, 10000)
    (amount0, amount1) = pool.collect(accounts[0], -240, 0, MAX_UINT128, MAX_UINT128)
    assert amount0 == 120
    assert amount1 == 0


def test_addLiquidity_toLiquidityGross(initializedPool, accounts):
    print("addLiquidity to liquidity gross")
    pool, _, _, _, _, tickSpacing = initializedPool
    pool.mint(accounts[0], -240, 0, 100)
    assert pool.ticks[-240].liquidityGross == 100
    assert pool.ticks[0].liquidityGross == 100
    # No liquidityGross === tick doesn't exist
    assert not pool.ticks.__contains__(tickSpacing)
    assert not pool.ticks.__contains__(tickSpacing * 2)
    pool.mint(accounts[0], -240, tickSpacing, 150)
    assert pool.ticks[-240].liquidityGross == 250
    assert pool.ticks[0].liquidityGross == 100
    assert pool.ticks[tickSpacing].liquidityGross == 150
    # No liquidityGross === tick doesn't exist
    assert not pool.ticks.__contains__(tickSpacing * 2)
    pool.mint(accounts[0], 0, tickSpacing * 2, 60)
    assert pool.ticks[-240].liquidityGross == 250
    assert pool.ticks[0].liquidityGross == 160
    assert pool.ticks[tickSpacing].liquidityGross == 150
    assert pool.ticks[tickSpacing * 2].liquidityGross == 60


def test_removeLiquidity_fromLiquidityGross(initializedPool, accounts):
    print("removes liquidity from liquidityGross")
    pool, _, _, _, _, _ = initializedPool
    pool.mint(accounts[0], -240, 0, 100)
    pool.mint(accounts[0], -240, 0, 40)
    pool.burn(accounts[0], -240, 0, 90)
    assert pool.ticks[-240].liquidityGross == 50
    assert pool.ticks[0].liquidityGross == 50


def test_clearTickLower_ifLastPositionRemoved(initializedPool, accounts):
    print("clears tick lower if last position is removed")
    pool, _, _, _, _, _ = initializedPool
    pool.mint(accounts[0], -240, 0, 100)
    pool.burn(accounts[0], -240, 0, 100)
    # tick cleared == not in ticks
    assert not pool.ticks.__contains__(-240)


def test_clearTickUpper_ifLastPositionRemoved(initializedPool, accounts):
    print("clears tick upper if last position is removed")
    pool, _, _, _, _, _ = initializedPool
    pool.mint(accounts[0], -240, 0, 100)
    pool.burn(accounts[0], -240, 0, 100)
    # tick cleared == not in ticks
    assert not pool.ticks.__contains__(0)


def test_clearsTick_ifNotUser(initializedPool, accounts):
    print("only clears the tick that is not used at all")
    pool, _, _, _, _, tickSpacing = initializedPool
    pool.mint(accounts[0], -240, 0, 100)
    pool.mint(accounts[1], -tickSpacing, 0, 250)
    pool.burn(accounts[0], -240, 0, 100)
    # tick cleared == not in ticks
    assert not pool.ticks.__contains__(-240)
    tickInfo = pool.ticks[-tickSpacing]
    assert tickInfo.liquidityGross == 250
    assert tickInfo.feeGrowthOutside0X128 == 0
    assert tickInfo.feeGrowthOutside1X128 == 0


# Including current price
def test_transferCurrentPriceTokens(initializedPool, accounts):
    print("price within range: transfers current price of both tokens")
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    (amount0, amount1) = pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 100)
    assert amount0 == 317
    assert amount1 == 32
    assert pool.balances[pool.token0] == 9996 + 317
    assert pool.balances[pool.token1] == 1000 + 32


def test_initializes_lowerTick(initializedPool, accounts):
    print("initializes lower tick")
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 100)
    liquidityGross = pool.ticks[minTick + tickSpacing].liquidityGross
    assert liquidityGross == 100


def test_initializes_upperTick(initializedPool, accounts):
    print("initializes upper tick")
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 100)
    liquidityGross = pool.ticks[maxTick - tickSpacing].liquidityGross
    assert liquidityGross == 100


def test_works_minMaxTick(initializedPool, accounts):
    print("works for min/ max tick")
    pool, _, minTick, maxTick, _, _ = initializedPool
    (amount0, amount1) = pool.mint(accounts[0], minTick, maxTick, 10000)
    assert amount0 == 31623
    assert amount1 == 3163
    assert pool.balances[pool.token0] == 9996 + 31623
    assert pool.balances[pool.token1] == 1000 + 3163


def test_removing_includesCurrentPrice(initializedPool, accounts):
    print("removing works")
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 100)
    pool.burn(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 100)
    (amount0, amount1) = pool.collect(
        accounts[0], minTick + tickSpacing, maxTick - tickSpacing, MAX_UINT128, MAX_UINT128
    )
    assert amount0 == 316
    assert amount1 == 31


# Below current price
def test_transfer_onlyToken1(initializedPool, accounts):
    print("transfers token1 only")
    pool, _, _, _, _, _ = initializedPool
    (amount0, amount1) = pool.mint(accounts[0], -46080, -23040, 10000)
    assert amount0 == 0
    assert amount1 == 2162
    assert pool.balances[pool.token0] == 9996
    assert pool.balances[pool.token1] == 1000 + 2162


def test_minTick_maxLeverage(initializedPool, accounts):
    print("min tick with max leverage")
    pool, _, minTick, _, _, tickSpacing = initializedPool
    pool.mint(accounts[0], minTick, minTick + tickSpacing, 2**102)
    assert pool.balances[pool.token0] == 9996
    assert pool.balances[pool.token1] == 1000 + 828011520


def test_works_minTick(initializedPool, accounts):
    print("works for min tick")
    pool, _, minTick, _, _, _ = initializedPool
    (amount0, amount1) = pool.mint(accounts[0], minTick, -23040, 10000)
    assert amount0 == 0
    assert amount1 == 3161
    assert pool.balances[pool.token0] == 9996
    assert pool.balances[pool.token1] == 1000 + 3161


def test_removing_belowCurrentPrice(initializedPool, accounts):
    print("removing works")
    pool, _, _, _, _, _ = initializedPool
    pool.mint(accounts[0], -46080, -46020, 10000)
    pool.burn(accounts[0], -46080, -46020, 10000)
    (amount0, amount1) = pool.collect(accounts[0], -46080, -46020, MAX_UINT128, MAX_UINT128)
    assert amount0 == 0
    assert amount1 == 3


def test_fees_duringSwap(initializedPool, accounts):
    print("protocol fees accumulate as expected during swap")
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    pool.setFeeProtocol(6, 6)

    pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, expandTo18Decimals(1))
    swapExact0For1(pool, expandTo18Decimals(1) // 10, accounts[0], None)
    swapExact1For0(pool, expandTo18Decimals(1) // 100, accounts[0], None)

    assert pool.protocolFees.token0 == 50000000000000
    assert pool.protocolFees.token1 == 5000000000000


def test_protectedPositions_beforefeesAreOn(initializedPool, accounts):
    print("positions are protected before protocol fee is turned on")
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, expandTo18Decimals(1))
    swapExact0For1(pool, expandTo18Decimals(1) // 10, accounts[0], None)
    swapExact1For0(pool, expandTo18Decimals(1) // 100, accounts[0], None)

    assert pool.protocolFees.token0 == 0
    assert pool.protocolFees.token1 == 0


def test_notAllowPoke_uninitialized_position(initializedPool, accounts):
    print("poke is not allowed on uninitialized position")
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    pool.mint(accounts[1], minTick + tickSpacing, maxTick - tickSpacing, expandTo18Decimals(1))
    swapExact0For1(pool, expandTo18Decimals(1) // 10, accounts[0], None)
    swapExact1For0(pool, expandTo18Decimals(1) // 100, accounts[0], None)
    # Modified revert reason
    tryExceptHandler(
        pool.burn,
        "NP",
        accounts[0],
        minTick + tickSpacing,
        maxTick - tickSpacing,
        0,
    )

    pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 1)

    position = pool.positions[getPositionKey(accounts[0], minTick + tickSpacing, maxTick - tickSpacing)]
    assert position.liquidity == 1
    assert position.feeGrowthInside0LastX128 == 102084710076281216349243831104605583
    assert position.feeGrowthInside1LastX128 == 10208471007628121634924383110460558
    assert position.tokensOwed0 == 0, "tokens owed 0 before"
    assert position.tokensOwed1 == 0, "tokens owed 1 before"

    pool.burn(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 1)
    position = pool.positions[getPositionKey(accounts[0], minTick + tickSpacing, maxTick - tickSpacing)]
    assert position.liquidity == 0
    assert position.feeGrowthInside0LastX128 == 102084710076281216349243831104605583
    assert position.feeGrowthInside1LastX128 == 10208471007628121634924383110460558
    assert position.tokensOwed0 == 3, "tokens owed 0 before"
    assert position.tokensOwed1 == 0, "tokens owed 1 before"


# Burn

## the combined amount of liquidity that the pool is initialized with (including the 1 minimum liquidity that is burned)
initializeLiquidityAmount = expandTo18Decimals(2)


def initializeAtZeroTick(pool, accounts):
    pool.initialize(encodePriceSqrt(1, 1))
    tickSpacing = pool.tickSpacing
    [min, max] = [getMinTick(tickSpacing), getMaxTick(tickSpacing)]
    pool.mint(accounts[0], min, max, initializeLiquidityAmount)


@pytest.fixture
def mediumPoolInitializedAtZero(createPoolMedium, accounts):
    pool, _, _, _, _, _ = createPoolMedium
    initializeAtZeroTick(pool, accounts)
    return createPoolMedium


def checkTickIsClear(pool, tick):
    assert pool.ticks.__contains__(tick) == False


def checkTickIsNotClear(pool, tick):
    # Make check explicit
    assert pool.ticks.__contains__(tick)
    assert pool.ticks[tick].liquidityGross != 0


def test_notClearPosition_ifNoMoreLiquidity(accounts, mediumPoolInitializedAtZero):
    pool, _, minTick, maxTick, _, tickSpacing = mediumPoolInitializedAtZero
    print("does not clear the position fee growth snapshot if no more liquidity")
    ## some activity that would make the ticks non-zero
    pool.mint(accounts[1], minTick, maxTick, expandTo18Decimals(1))
    print(pool.slot0.tick)
    swapExact0For1(pool, expandTo18Decimals(1), accounts[0], None)
    swapExact1For0(pool, expandTo18Decimals(1), accounts[0], None)
    pool.burn(accounts[1], minTick, maxTick, expandTo18Decimals(1))
    tickInfo = pool.positions[getPositionKey(accounts[1], minTick, maxTick)]
    assert tickInfo.liquidity == 0
    assert tickInfo.tokensOwed0 != 0
    assert tickInfo.tokensOwed1 != 0
    assert tickInfo.feeGrowthInside0LastX128 == 340282366920938463463374607431768211
    # Original value: 340282366920938463463374607431768211
    assert tickInfo.feeGrowthInside1LastX128 == 340282366920938463463374607431768211


# Continue UniswapV3Pool.spects.ts line 596
def test_clearsTick_ifLastPosition(accounts, mediumPoolInitializedAtZero):
    print("clears the tick if its the last position using it")
    pool, _, minTick, maxTick, _, tickSpacing = mediumPoolInitializedAtZero
    tickLower = minTick + tickSpacing
    tickUpper = maxTick - tickSpacing
    ## some activity that would make the ticks non-zero
    pool.mint(accounts[0], tickLower, tickUpper, 1)
    swapExact0For1(pool, expandTo18Decimals(1), accounts[0], None)
    pool.burn(accounts[0], tickLower, tickUpper, 1)
    checkTickIsClear(pool, tickLower)
    checkTickIsClear(pool, tickUpper)


def test_clearOnlyLower_ifUpperUsed(accounts, mediumPoolInitializedAtZero):
    print("clears only the lower tick if upper is still used")
    pool, _, minTick, maxTick, _, tickSpacing = mediumPoolInitializedAtZero
    tickLower = minTick + tickSpacing
    tickUpper = maxTick - tickSpacing
    ## some activity that would make the ticks non-zero
    pool.mint(accounts[0], tickLower, tickUpper, 1)
    pool.mint(accounts[0], tickLower + tickSpacing, tickUpper, 1)
    swapExact0For1(pool, expandTo18Decimals(1), accounts[0], None)
    pool.burn(accounts[0], tickLower, tickUpper, 1)
    checkTickIsClear(pool, tickLower)
    checkTickIsNotClear(pool, tickUpper)


def test_clearsOnlyUpper_ifLowerUsed(accounts, mediumPoolInitializedAtZero):
    print("clears only the upper tick if lower is still used")
    pool, _, minTick, maxTick, _, tickSpacing = mediumPoolInitializedAtZero
    tickLower = minTick + tickSpacing
    tickUpper = maxTick - tickSpacing
    ## some activity that would make the ticks non-zero
    pool.mint(accounts[0], tickLower, tickUpper, 1)
    pool.mint(accounts[0], tickLower, tickUpper - tickSpacing, 1)
    swapExact0For1(pool, expandTo18Decimals(1), accounts[0], None)
    pool.burn(accounts[0], tickLower, tickUpper, 1)
    checkTickIsNotClear(pool, tickLower)
    checkTickIsClear(pool, tickUpper)


# Miscellaneous mint tests
@pytest.fixture
def lowPoolInitializedAtZero(createPoolLow, accounts):
    pool, _, _, _, _, _ = createPoolLow
    initializeAtZeroTick(pool, accounts)
    return createPoolLow


def test_mintRight_currentPrice(lowPoolInitializedAtZero, accounts):
    print("mint to the right of the current price")
    pool, _, _, _, _, tickSpacing = lowPoolInitializedAtZero
    liquidityDelta = 1000
    lowerTick = tickSpacing
    upperTick = tickSpacing * 2
    liquidityBefore = pool.liquidity
    b0 = pool.balances[TEST_TOKENS[0]]
    b1 = pool.balances[TEST_TOKENS[1]]

    pool.mint(accounts[0], lowerTick, upperTick, liquidityDelta)

    liquidityAfter = pool.liquidity
    assert liquidityAfter >= liquidityBefore

    assert pool.balances[TEST_TOKENS[0]] - b0 == 1
    assert pool.balances[TEST_TOKENS[1]] - b1 == 0


def test_mintLeft_currentPrice(lowPoolInitializedAtZero, accounts):
    print("mint to the right of the current price")
    pool, _, _, _, _, tickSpacing = lowPoolInitializedAtZero
    liquidityDelta = 1000
    lowerTick = -tickSpacing * 2
    upperTick = -tickSpacing
    liquidityBefore = pool.liquidity
    b0 = pool.balances[TEST_TOKENS[0]]
    b1 = pool.balances[TEST_TOKENS[1]]

    pool.mint(accounts[0], lowerTick, upperTick, liquidityDelta)

    liquidityAfter = pool.liquidity
    assert liquidityAfter >= liquidityBefore

    assert pool.balances[TEST_TOKENS[0]] - b0 == 0
    assert pool.balances[TEST_TOKENS[1]] - b1 == 1


def test_mint_withinCurrentPrice(lowPoolInitializedAtZero, accounts):
    print("mint within the current price")
    pool, _, _, _, _, tickSpacing = lowPoolInitializedAtZero
    liquidityDelta = 1000
    lowerTick = -tickSpacing
    upperTick = tickSpacing
    liquidityBefore = pool.liquidity
    b0 = pool.balances[TEST_TOKENS[0]]
    b1 = pool.balances[TEST_TOKENS[1]]

    pool.mint(accounts[0], lowerTick, upperTick, liquidityDelta)

    liquidityAfter = pool.liquidity
    assert liquidityAfter >= liquidityBefore

    assert pool.balances[TEST_TOKENS[0]] - b0 == 1
    assert pool.balances[TEST_TOKENS[1]] - b1 == 1


def test_cannotRemove_moreThanPosition(lowPoolInitializedAtZero, accounts):
    print("cannot remove more than the entire position")
    pool, _, _, _, _, tickSpacing = lowPoolInitializedAtZero
    lowerTick = -tickSpacing
    upperTick = tickSpacing

    pool.mint(accounts[0], lowerTick, upperTick, expandTo18Decimals(1000))

    tryExceptHandler(pool.burn, "LS", accounts[0], lowerTick, upperTick, expandTo18Decimals(1001))


def test_collectFee_currentPrice(lowPoolInitializedAtZero, accounts):
    print("collect fees within the current price after swap")
    pool, _, _, _, _, tickSpacing = lowPoolInitializedAtZero
    liquidityDelta = expandTo18Decimals(100)
    lowerTick = -tickSpacing * 100
    upperTick = tickSpacing * 100

    pool.mint(accounts[0], lowerTick, upperTick, liquidityDelta)

    liquidityBefore = pool.liquidity

    amount0In = expandTo18Decimals(1)

    swapExact0For1(pool, amount0In, accounts[0], None)

    liquidityAfter = pool.liquidity

    assert liquidityAfter >= liquidityBefore, "k increases"

    token0BalanceBeforePool = pool.balances[TEST_TOKENS[0]]
    token1BalanceBeforePool = pool.balances[TEST_TOKENS[1]]
    token0BalanceBeforeWallet = accounts[0].balances[TEST_TOKENS[0]]
    token1BalanceBeforeWallet = accounts[0].balances[TEST_TOKENS[1]]

    pool.burn(accounts[0], lowerTick, upperTick, 0)
    pool.collect(accounts[0], lowerTick, upperTick, MAX_UINT128, MAX_UINT128)

    pool.burn(accounts[0], lowerTick, upperTick, 0)

    (fees0, fees1) = pool.collect(accounts[0], lowerTick, upperTick, MAX_UINT128, MAX_UINT128)

    assert fees0 == 0
    assert fees1 == 0

    token0BalanceAfterPool = pool.balances[TEST_TOKENS[0]]
    token1BalanceAfterPool = pool.balances[TEST_TOKENS[1]]
    token0BalanceAfterWallet = accounts[0].balances[TEST_TOKENS[0]]
    token1BalanceAfterWallet = accounts[0].balances[TEST_TOKENS[1]]

    assert token0BalanceAfterWallet > token0BalanceBeforeWallet
    assert token1BalanceAfterWallet == token1BalanceBeforeWallet
    assert token0BalanceAfterPool < token0BalanceBeforePool
    assert token1BalanceAfterPool == token1BalanceBeforePool


# pre-initialize at medium fee
def test_preInitialized_mediumFee(createPoolMedium):
    print("pre-initialized at medium fee")
    pool, _, _, _, _, _ = createPoolMedium
    assert pool.liquidity == 0


# post-initialize at medium fee
def test_initialLiquidity(mediumPoolInitializedAtZero):
    print("returns initial liquidity")
    pool, _, _, _, _, _ = mediumPoolInitializedAtZero
    assert pool.liquidity == expandTo18Decimals(2)


def test_supplyInRange(mediumPoolInitializedAtZero, accounts):
    print("returns in supply in range")
    pool, _, _, _, _, tickSpacing = mediumPoolInitializedAtZero
    pool.mint(accounts[0], -tickSpacing, tickSpacing, expandTo18Decimals(3))
    assert pool.liquidity == expandTo18Decimals(5)


def test_excludeSupply_tickAboveCurrentTick(mediumPoolInitializedAtZero, accounts):
    print("excludes supply at tick above current tick")
    pool, _, _, _, _, tickSpacing = mediumPoolInitializedAtZero
    pool.mint(accounts[0], tickSpacing, tickSpacing * 2, expandTo18Decimals(3))
    assert pool.liquidity == expandTo18Decimals(2)


def test_excludeSupply_tickBelowCurrentTick(mediumPoolInitializedAtZero, accounts):
    print("excludes supply at tick below current tick")
    pool, _, _, _, _, tickSpacing = mediumPoolInitializedAtZero
    pool.mint(accounts[0], -tickSpacing * 2, -tickSpacing, expandTo18Decimals(3))
    assert pool.liquidity == expandTo18Decimals(2)


def test_updatesWhenExitingRange(mediumPoolInitializedAtZero, accounts):
    print("updates correctly when exiting range")
    pool, _, _, _, _, tickSpacing = mediumPoolInitializedAtZero

    kBefore = pool.liquidity
    assert kBefore == expandTo18Decimals(2)

    ## add liquidity at and above current tick
    liquidityDelta = expandTo18Decimals(1)
    lowerTick = 0
    upperTick = tickSpacing
    pool.mint(accounts[0], lowerTick, upperTick, liquidityDelta)

    ## ensure virtual supply has increased appropriately
    kAfter = pool.liquidity
    assert kAfter == expandTo18Decimals(3)

    ## swap toward the left (just enough for the tick transition function to trigger)
    swapExact0For1(pool, 1, accounts[0], None)
    assert pool.slot0.tick == -1

    kAfterSwap = pool.liquidity
    assert kAfterSwap == expandTo18Decimals(2)


def test_updatesWhenEnteringRange(mediumPoolInitializedAtZero, accounts):
    print("updates correctly when entering range")
    pool, _, _, _, _, tickSpacing = mediumPoolInitializedAtZero

    kBefore = pool.liquidity
    assert kBefore == expandTo18Decimals(2)

    ## add liquidity at and below current tick
    liquidityDelta = expandTo18Decimals(1)
    lowerTick = -tickSpacing
    upperTick = 0
    pool.mint(accounts[0], lowerTick, upperTick, liquidityDelta)

    ## ensure virtual supply has increased appropriately
    kAfter = pool.liquidity
    assert kAfter == kBefore
    ## swap toward the right (just enough for the tick transition function to trigger)
    swapExact0For1(pool, 1, accounts[0], None)
    assert pool.slot0.tick == -1

    kAfterSwap = pool.liquidity
    assert kAfterSwap == expandTo18Decimals(3)


# Limit orders


def test_limitSelling0For1_atTick0Thru1(mediumPoolInitializedAtZero, accounts):
    print("limit selling 0 for 1 at tick 0 thru 1")
    pool, _, _, _, _, _ = mediumPoolInitializedAtZero

    (amount0, amount1) = pool.mint(accounts[0], 0, 120, expandTo18Decimals(1))
    assert amount0 == 5981737760509663
    assert amount1 == 0

    ## somebody takes the limit order
    swapExact1For0(pool, expandTo18Decimals(2), accounts[0], None)
    (recipient, tickLower, tickUpper, amount, amount0, amount1) = pool.burn(
        accounts[0], 0, 120, expandTo18Decimals(1)
    )
    assert (recipient, tickLower, tickUpper, amount, amount0, amount1) == (
        accounts[0],
        0,
        120,
        expandTo18Decimals(1),
        0,
        6017734268818165,
    )

    token1BalanceBeforeWallet = accounts[0].balances[TEST_TOKENS[1]]
    pool.collect(accounts[0], 0, 120, MAX_UINT128, MAX_UINT128)
    token1BalanceAfterWallet = accounts[0].balances[TEST_TOKENS[1]]

    amountTranferred = token1BalanceAfterWallet - token1BalanceBeforeWallet

    assert recipient == accounts[0]
    assert amountTranferred == 6017734268818165 + 18107525382602

    assert pool.slot0.tick >= 120
