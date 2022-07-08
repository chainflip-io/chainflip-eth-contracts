from utilities import *
from UniswapPool import *
from Factory import *
from poolFixtures import *

from test_uniswapPool import accounts

import pytest
import copy

# Doing only one pool now to debug
#@pytest.fixture(params=[0, 1])
@pytest.fixture(params=[0])
def TEST_POOLS(request, accounts):
    poolFixture = request.getfixturevalue("pool{}".format(request.param))
    feeAmount = poolFixture.feeAmount
    tickSpacing = poolFixture.tickSpacing
    pool = UniswapPool(TEST_TOKENS[0], TEST_TOKENS[1], feeAmount, tickSpacing)
    pool.initialize(poolFixture.startingPrice)
    for position in poolFixture.positions:
        pool.mint(accounts[0], position.tickLower, position.tickUpper, position.liquidity)
    poolBalance0 = pool.balances[TEST_TOKENS[0]]
    poolBalance1 = pool.balances[TEST_TOKENS[1]]
    return TEST_TOKENS[0], TEST_TOKENS[1], pool, poolBalance0, poolBalance1, accounts[1], poolFixture


@pytest.fixture
def afterEach(accounts, TEST_POOLS):
    yield
    # Comment out while debugging
    #print("check can burn positions")
    # (_, _, pool, _, _, _, poolFixture) = TEST_POOLS
    # for position in poolFixture.positions:
    #     pool.burn(accounts[0], position.tickLower, position.tickUpper, position.liquidity)
    #     pool.collect(accounts[0], position.tickLower, position.tickUpper, MAX_UINT128, MAX_UINT128)


# UniswapV3Pool swap tests


@pytest.mark.usefixtures("afterEach")
def test_example(accounts, TEST_POOLS):
    assert True


@pytest.mark.usefixtures("afterEach")
def test_testing(TEST_POOLS, accounts):
    print("TBD")
    (_, _, pool, poolBalance0, poolBalance1, recipient, poolFixture) = TEST_POOLS

    if poolFixture.swapTests == None:
        swapTests = DEFAULT_POOL_SWAP_TESTS
    else:
        swapTests = poolFixture.swapTests

    for testCase in swapTests:
        slot0 = pool.slot0
        poolInstance = copy.deepcopy(pool)
        print(testCase)
        recipient, amount0, amount1, sqrtPriceX96, liquidity, tick = executeSwap(poolInstance, testCase, recipient)

        poolBalance0After = poolInstance.balances[TEST_TOKENS[0]]
        poolBalance1After = poolInstance.balances[TEST_TOKENS[1]]
        slot0After = poolInstance.slot0
        liquidityAfter = poolInstance.liquidity
        feeGrowthGlobal0X128 = poolInstance.feeGrowthGlobal0X128
        feeGrowthGlobal1X128 = poolInstance.feeGrowthGlobal1X128

        poolBalance0Delta = poolBalance0After - poolBalance0
        poolBalance1Delta = poolBalance1After - poolBalance1

        ## check all the events were emitted corresponding to balance changes
        if poolBalance0Delta == 0:
            amount0 == 0
        elif poolBalance0Delta <= 0:
            amount0 == - poolBalance0Delta
        else:
            amount0 == poolBalance0Delta

        if poolBalance1Delta == 0:
            amount1 == 0
        elif poolBalance1Delta <= 0:
            amount1 == - poolBalance1Delta
        else:
            amount1 == poolBalance1Delta
        
        # TODO: check that the swap event was emitted too
        if poolBalance0Delta != 0:
            executionPrice = - (poolBalance1Delta / poolBalance0Delta)
        else:
            executionPrice = "-Infinity"

        print("Swap results")
        print(f'amount0Before: {poolBalance0}')
        print(f'amount0Delta: {poolBalance0Delta}')
        print(f'amount1Before: {poolBalance1}')
        print(f'amount1Delta: {poolBalance1Delta}')
        print(f'executionPrice: {executionPrice}')
        print(f'feeGrowthGlobal0X128Delta: {feeGrowthGlobal0X128}')
        print(f'feeGrowthGlobal1X128Delta: {feeGrowthGlobal1X128}')
        print(f'poolPriceAfter: {formatPrice(slot0After.sqrtPriceX96)}')  #same as $sqrtPriceX96
        print(f'poolPriceBefore: {formatPrice(slot0.sqrtPriceX96)}')       
        print(f'tickAfter: {slot0After.tick}') #same as $tick
        print(f'tickBefore: {slot0.tick}')


        print("SUCCESFUL TEST because we are not checking anything right now")

    #assert False



def executeSwap(pool, testCase, recipient):
    sqrtPriceLimit = None if not testCase.__contains__("sqrtPriceLimit") else testCase["sqrtPriceLimit"]
    if testCase.__contains__("exactOut"):
        if testCase["exactOut"]:
            if testCase["zeroForOne"]:
                return swap0ForExact1(pool, testCase["amount1"], recipient, sqrtPriceLimit)
            else:
                return swap1ForExact0(pool, testCase["amount0"], recipient, sqrtPriceLimit)
        else:
            if testCase["zeroForOne"]:
                return swapExact0For1(pool, testCase["amount0"], recipient, sqrtPriceLimit)
            else:
                return swapExact1For0(pool, testCase["amount1"], recipient, sqrtPriceLimit)
    else:
        if testCase["zeroForOne"]:
            return swapToLowerPrice(pool, recipient, testCase["sqrtPriceLimit"])
        else:
            return swapToHigherPrice(pool, recipient, testCase["sqrtPriceLimit"])
