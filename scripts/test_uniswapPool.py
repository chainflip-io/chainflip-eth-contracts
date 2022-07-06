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

