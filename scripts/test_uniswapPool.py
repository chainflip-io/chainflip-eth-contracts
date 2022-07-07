from utilities import *
from UniswapPool import *
from Factory import *

import pytest

@pytest.fixture
def accounts():
    # Fund them with infinite tokens
    account0 = Account("ALICE",TEST_TOKENS, [MAX_INT256, MAX_INT256])
    account1 = Account("BOB", TEST_TOKENS, [MAX_INT256, MAX_INT256])
    return account0,account1

@pytest.fixture
def createPool():
    factory = Factory()
    feeAmount = FeeAmount.MEDIUM
    tickSpacing = TICK_SPACINGS[FeeAmount.MEDIUM]
    pool = factory.createPool(TEST_TOKENS[0],TEST_TOKENS[1], FeeAmount.MEDIUM)
    minTick = getMinTick(tickSpacing)
    maxTick = getMaxTick(tickSpacing)
    return pool, factory, minTick, maxTick, feeAmount, tickSpacing

@pytest.fixture
def initializedPool(createPool, accounts):
    pool, _, minTick, maxTick, _, _ = createPool
    pool.initialize(encodePriceSqrt(1, 10))
    pool.mint(accounts[0], minTick, maxTick, 3161)    
    return createPool

def test_constructor(createPool):
    print('constructor initializes immutables')
    pool, factory, _, _, _, _ = createPool
    assert factory.getPool[0] == [TEST_TOKENS[0], TEST_TOKENS[1], FeeAmount.MEDIUM]
    assert pool.token0 == TEST_TOKENS[0]
    assert pool.token1 == TEST_TOKENS[1]

# Initialize
def test_fails_alreadyInitialized(createPool):
    print('fails if already initialized')
    pool, _, _, _, _, _ = createPool
    pool.initialize(encodePriceSqrt(1, 1))
    tryExceptHandler(pool.initialize, "AI", encodePriceSqrt(1, 1))  

def test_fails_lowStartingPrice(createPool):
    pool, _, _, _, _, _ = createPool
    print('fails if already initialized')
    tryExceptHandler(pool.initialize,  "R", 1)
    tryExceptHandler(pool.initialize,  "R", TickMath.MIN_SQRT_RATIO - 1)

def test_fails_highStartingPrice(createPool):
    print('fails if already initialized')
    pool, _, _, _, _, _ = createPool
    tryExceptHandler(pool.initialize,  "R", TickMath.MAX_SQRT_RATIO)
    tryExceptHandler(pool.initialize,  "R", MAX_UINT160)

def test_initialize_MIN_SQRT_RATIO(createPool):
    print('can be initialized at MIN_SQRT_RATIO')
    pool, _, _, _, _, _ = createPool
    pool.initialize(TickMath.MIN_SQRT_RATIO)
    assert pool.slot0.tick == getMinTick(1)

def test_initialize_MAX_SQRT_RATIO_minusOne(createPool):
    print('can be initialized at MAX_SQRT_RATIO - 1')
    pool, _, _, _, _, _ = createPool
    pool.initialize(TickMath.MAX_SQRT_RATIO - 1)
    assert pool.slot0.tick == getMaxTick(1) - 1

def test_setInitialVariables(createPool):
    print('sets initial variables')
    pool, _, _, _, _, _ = createPool
    price = encodePriceSqrt(1, 2)
    pool.initialize(price)

    assert pool.slot0.sqrtPriceX96 == price
    assert pool.slot0.tick == -6932
    
# Mint

def test_initialize_10to1(createPool, accounts):
    pool, _, minTick, maxTick, _, _ = createPool
    pool.initialize(encodePriceSqrt(1, 10))
    pool.mint(accounts[0], minTick, maxTick, 3161)

def test_fails_tickLower_gtTickUpper(initializedPool, accounts):
    print('fails if tickLower greater than tickUpper')
    pool, _, _, _, _, _ = initializedPool
    tryExceptHandler(pool.mint, "TLU", accounts[0], 1,0,1)

def test_fails_tickLower_ltMinTick(initializedPool, accounts):
    print('fails if tickLower less than min Tick')
    pool, _, _, _, _, _ = initializedPool
    tryExceptHandler(pool.mint, "TLM", accounts[0], -887273, 0, 1)

def test_fails_tickUpper_gtMaxTick(initializedPool, accounts):
    print('fails if tickUpper greater than max Tick')
    pool, _, _, _, _, _ = initializedPool
    tryExceptHandler(pool.mint, "TUM", accounts[0], 0, 887273, 1)

def test_fails_amountGtMax(initializedPool, accounts):
    print('fails if amount exceeds the max')
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    maxLiquidityGross = pool.maxLiquidityPerTick
    tryExceptHandler(pool.mint, "LO", accounts[0], minTick + tickSpacing, maxTick - tickSpacing, maxLiquidityGross + 1)
    pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, maxLiquidityGross)

def test_fails_totalAmountatTick_gtMAX(initializedPool, accounts):
    print('fails if total amount at tick exceeds the max')
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 1000)

    maxLiquidityGross = pool.maxLiquidityPerTick
    tryExceptHandler(pool.mint, "LO", accounts[0], minTick + tickSpacing, maxTick - tickSpacing, maxLiquidityGross - 1000 + 1)
    tryExceptHandler(pool.mint, "LO", accounts[0], minTick + tickSpacing * 2, maxTick - tickSpacing, maxLiquidityGross - 1000+1)
    tryExceptHandler(pool.mint, "LO", accounts[0], minTick + tickSpacing, maxTick - tickSpacing * 2, maxLiquidityGross - 1000 + 1)
    pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, maxLiquidityGross - 1000)

def test_fails_zeroAmount(initializedPool, accounts):
    print('fails if amount is zero')
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    tryExceptHandler(pool.mint, "", accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 0)

# Success cases

def test_initial_balances(initializedPool):
    print('fails if amount is zero')
    pool, _, _, _, _, _ = initializedPool
    assert pool.balances[pool.token0] == 9996
    assert pool.balances[pool.token1] == 1000

def test_initialTick(initializedPool):
    print('fails if amount is zero')
    pool, _, _, _, _, _ = initializedPool
    assert pool.slot0.tick == -23028

# Above current tick
def test_transferToken0_only(initializedPool, accounts):
    print('transferToken0 only')
    pool, _, _, _, _, _ = initializedPool
    (amount0, amount1) = pool.mint(accounts[0], -22980, 0, 10000)
    assert amount0 != 0
    assert amount1 == 0
    assert pool.balances[pool.token0] == 9996 + 21549
    assert pool.balances[pool.token1] == 1000    

def test_maxTick_maxLeverage(initializedPool, accounts):
    print('max tick with max leverage')
    pool, _, _, maxTick, _, tickSpacing = initializedPool
    pool.mint(accounts[0], maxTick - tickSpacing, maxTick, 2**102)
    assert pool.balances[pool.token0] == 9996 + 828011525
    assert pool.balances[pool.token1] == 1000

def test_maxTick(initializedPool, accounts):
    print('works for max tick')
    pool, _, _, maxTick, _, _ = initializedPool
    pool.mint(accounts[0], -22980, maxTick, 10000)
    assert pool.balances[pool.token0] == 9996 + 31549
    assert pool.balances[pool.token1] == 1000

def test_remove_aboveCurrentPrice(initializedPool, accounts):
    print('removing works')
    pool, _, _, _, _, _ = initializedPool
    pool.mint(accounts[0], -240, 0, 10000)
    pool.burn(accounts[0],-240, 0, 10000)
    ( amount0, amount1 ) = pool.collect(accounts[0], -240, 0, MAX_UINT128, MAX_UINT128)
    assert amount0 == 120
    assert amount1 == 0

def test_addLiquidity_toLiquidityGross(initializedPool, accounts):
    print('addLiquidity to liquidity gross')
    pool, _, _, _, _, tickSpacing = initializedPool
    pool.mint(accounts[0], -240, 0, 100)
    assert pool.ticks[-240].liquidityGross == 100
    assert pool.ticks[0].liquidityGross == 100
    # No liquidityGross === tick doesn't exist
    assert not pool.ticks.__contains__(tickSpacing)
    assert not pool.ticks.__contains__(tickSpacing*2)
    pool.mint(accounts[0], -240, tickSpacing, 150)
    assert pool.ticks[-240].liquidityGross == 250
    assert pool.ticks[0].liquidityGross == 100
    assert pool.ticks[tickSpacing].liquidityGross == 150
    # No liquidityGross === tick doesn't exist
    assert not pool.ticks.__contains__(tickSpacing*2)
    pool.mint(accounts[0], 0, tickSpacing * 2, 60)
    assert pool.ticks[-240].liquidityGross == 250
    assert pool.ticks[0].liquidityGross == 160
    assert pool.ticks[tickSpacing].liquidityGross == 150
    assert pool.ticks[tickSpacing * 2].liquidityGross == 60   


def test_removeLiquidity_fromLiquidityGross(initializedPool, accounts):
    print('removes liquidity from liquidityGross')
    pool, _, _, _, _, _ = initializedPool
    pool.mint(accounts[0], -240, 0, 100)
    pool.mint(accounts[0], -240, 0, 40)
    pool.burn(accounts[0],-240, 0, 90)
    assert pool.ticks[-240].liquidityGross == 50
    assert pool.ticks[0].liquidityGross == 50

def test_clearTickLower_ifLastPositionRemoved(initializedPool, accounts):
    print('clears tick lower if last position is removed')
    pool, _, _, _, _, _ = initializedPool
    pool.mint(accounts[0], -240, 0, 100)
    pool.burn(accounts[0],-240, 0, 100)
    # tick cleared == not in ticks
    assert not pool.ticks.__contains__(-240)    

def test_clearTickUpper_ifLastPositionRemoved(initializedPool, accounts):
    print('clears tick upper if last position is removed')
    pool, _, _, _, _, _ = initializedPool
    pool.mint(accounts[0], -240, 0, 100)
    pool.burn(accounts[0],-240, 0, 100)
    # tick cleared == not in ticks
    assert not pool.ticks.__contains__(0)

def test_clearsTick_ifNotUser(initializedPool, accounts):
    print('only clears the tick that is not used at all')
    pool, _, _, _, _, tickSpacing = initializedPool
    pool.mint(accounts[0], -240, 0, 100)
    pool.mint(accounts[1], -tickSpacing, 0, 250)
    pool.burn(accounts[0],-240, 0, 100)
    # tick cleared == not in ticks
    assert not pool.ticks.__contains__(-240)    
    tickInfo = pool.ticks[-tickSpacing]
    assert tickInfo.liquidityGross == 250
    assert tickInfo.feeGrowthOutside0X128 == 0
    assert tickInfo.feeGrowthOutside1X128 == 0

# Including current price
def test_transferCurrentPriceTokens(initializedPool, accounts):
    print('price within range: transfers current price of both tokens')
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    (amount0, amount1) = pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 100)
    assert amount0 == 317
    assert amount1 == 32
    assert pool.balances[pool.token0] == 9996 + 317
    assert pool.balances[pool.token1] == 1000 + 32

def test_initializes_lowerTick(initializedPool, accounts):
    print('initializes lower tick')
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 100)
    liquidityGross =  pool.ticks[minTick + tickSpacing].liquidityGross
    assert liquidityGross == 100

def test_initializes_upperTick(initializedPool, accounts):
    print('initializes upper tick')
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 100)
    liquidityGross =  pool.ticks[maxTick - tickSpacing].liquidityGross
    assert liquidityGross == 100

def test_works_minMaxTick(initializedPool, accounts):
    print('works for min/ max tick')
    pool, _, minTick, maxTick, _, _ = initializedPool
    (amount0, amount1) = pool.mint(accounts[0], minTick, maxTick, 10000)
    assert amount0 == 31623
    assert amount1 == 3163    
    assert pool.balances[pool.token0] == 9996 + 31623
    assert pool.balances[pool.token1] == 1000 + 3163

def test_removing_includesCurrentPrice(initializedPool, accounts):
    print('removing works')
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    pool.mint(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, 100)
    pool.burn(accounts[0],minTick + tickSpacing, maxTick - tickSpacing, 100)
    ( amount0, amount1 ) = pool.collect(accounts[0], minTick + tickSpacing, maxTick - tickSpacing, MAX_UINT128, MAX_UINT128)
    assert amount0 == 316
    assert amount1 == 31

# Below current price
def test_transfer_onlyToken1(initializedPool, accounts):
    print('transfers token1 only')
    pool, _, _, _, _, _ = initializedPool
    (amount0, amount1) = pool.mint(accounts[0], -46080, -23040, 10000)
    assert amount0 == 0
    assert amount1 == 2162
    assert pool.balances[pool.token0] == 9996
    assert pool.balances[pool.token1] == 1000 + 2162

def test_minTick_maxLeverage(initializedPool, accounts):
    print('min tick with max leverage')
    pool, _, minTick, _, _, tickSpacing = initializedPool
    pool.mint(accounts[0], minTick, minTick + tickSpacing, 2**102)
    assert pool.balances[pool.token0] == 9996
    assert pool.balances[pool.token1] == 1000 + 828011520

def test_works_minTick(initializedPool, accounts):
    print('works for min tick')
    pool, _, minTick, _, _, _ = initializedPool
    (amount0, amount1) = pool.mint(accounts[0], minTick, -23040, 10000)
    assert amount0 == 0
    assert amount1 == 3161    
    assert pool.balances[pool.token0] == 9996
    assert pool.balances[pool.token1] == 1000 + 3161

def test_removing_belowCurrentPrice(initializedPool, accounts):
    print('removing works')
    pool, _, minTick, _, _, tickSpacing = initializedPool
    pool.mint(accounts[0], -46080, -46020, 10000)
    pool.burn(accounts[0],-46080, -46020, 10000)
    ( amount0, amount1 ) = pool.collect(accounts[0], -46080, -46020, MAX_UINT128, MAX_UINT128)
    assert amount0 == 0
    assert amount1 == 3

### UTILITIES ###
def swapExact0For1(pool, amount, recipient, **kwargs):
    sqrtPriceLimitX96 = kwargs.get("sqrtPriceLimitX96", getSqrtPriceLimitX96(TEST_TOKENS[0]))
    return swap(pool, TEST_TOKENS[0], [amount, 0], recipient, sqrtPriceLimitX96)

def swap0ForExact1(pool , amount, recipient, **kwargs):
    sqrtPriceLimitX96 = kwargs.get("sqrtPriceLimitX96", getSqrtPriceLimitX96(TEST_TOKENS[0]))
    return swap(pool,TEST_TOKENS[0], [0, amount], recipient, sqrtPriceLimitX96)

def swapExact1For0(pool , amount, recipient, **kwargs):
    sqrtPriceLimitX96 = kwargs.get("sqrtPriceLimitX96", getSqrtPriceLimitX96(TEST_TOKENS[1]))
    return swap(pool,TEST_TOKENS[1], [amount, 0], recipient, sqrtPriceLimitX96)

def swap1ForExact0(pool , amount, recipient, **kwargs):
    sqrtPriceLimitX96 = kwargs.get("sqrtPriceLimitX96", getSqrtPriceLimitX96(TEST_TOKENS[1]))
    return swap(pool,TEST_TOKENS[1], [0, amount], recipient, sqrtPriceLimitX96)

def swap(pool, inputToken, amounts, recipient, sqrtPriceLimitX96):
    [amountIn, amountOut] = amounts
    exactInput = (amountOut == 0)
    amount = amountIn if exactInput else amountOut

    if inputToken == TEST_TOKENS[0]:
        if exactInput:
            checkInt128(amount)
            pool.swap(recipient, True, amount, sqrtPriceLimitX96)
        else:
            checkInt128(-amount)
            pool.swap(recipient, True, -amount, sqrtPriceLimitX96)
    else:
        if exactInput:
            checkInt128(amount)
            pool.swap(recipient, False, amount, sqrtPriceLimitX96)
        else:
            checkInt128(-amount)
            pool.swap(recipient, False, -amount, sqrtPriceLimitX96)

def getSqrtPriceLimitX96(inputToken):
    if inputToken == TEST_TOKENS[0]:
        return TickMath.MIN_SQRT_RATIO + 1
    else:
        return TickMath.MAX_SQRT_RATIO - 1


################

def test_fees_duringSwap(initializedPool, accounts):
    print('protocol fees accumulate as expected during swap')
    pool, _, minTick, maxTick, _, tickSpacing = initializedPool
    pool.setFeeProtocol(6,6)
    
    pool.mint(accounts[0],  minTick + tickSpacing, maxTick - tickSpacing, expandTo18Decimals(1))
    swapExact0For1(pool, expandTo18Decimals(1) // 10, accounts[0])
    swapExact1For0(pool, expandTo18Decimals(1) // 100, accounts[0])

    assert pool.protocolFees.token0 == 50000000000000
    assert pool.protocolFees.token1 == 5000000000000

