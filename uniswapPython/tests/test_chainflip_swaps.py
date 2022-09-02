import sys, os

from utilities import *
from poolFixturesChainflip import *
from test_chainflipPool import accounts, ledger
from UniswapV3PoolSwaps import swapsSnapshot

sys.path.append(os.path.join(os.path.dirname(sys.path[0]), "contracts"))
from UniswapPool import *
from Factory import *
from ChainflipPool import ChainflipPool

import pytest
import copy
import decimal


@pytest.fixture(params=[*range(9, 15, 1)])
def TEST_POOLS(request, accounts, ledger):
    poolFixture = request.getfixturevalue("poolCF{}".format(request.param))
    feeAmount = poolFixture.feeAmount
    tickSpacing = poolFixture.tickSpacing
    pool = ChainflipPool(TEST_TOKENS[0], TEST_TOKENS[1], feeAmount, tickSpacing, ledger)
    pool.initialize(poolFixture.startingPrice)
    for position in poolFixture.positions:
        pool.mint(
            accounts[0], position.tickLower, position.tickUpper, position.liquidity
        )

    liquidity0LO = 0
    liquidity1LO = 0
    for position in poolFixture.limitPositions:
        pool.mintLinearOrder(
            position.token, accounts[0], position.tick, position.liquidity
        )
        if position.token == pool.token0:
            liquidity0LO += position.liquidity
        else:
            liquidity1LO += position.liquidity

    # Make up for limit order tokens so it can be checked against uniswap balances
    poolBalance0 = pool.balances[TEST_TOKENS[0]] - liquidity0LO
    poolBalance1 = pool.balances[TEST_TOKENS[1]] - liquidity1LO

    return (
        TEST_TOKENS[0],
        TEST_TOKENS[1],
        pool,
        poolBalance0,
        poolBalance1,
        accounts[1],
        poolFixture,
    )


@pytest.fixture
def afterEach(accounts, TEST_POOLS):
    yield
    print("check can burn positions")
    (_, _, pool, _, _, _, poolFixture) = TEST_POOLS
    for position in poolFixture.positions:
        pool.burn(
            accounts[0], position.tickLower, position.tickUpper, position.liquidity
        )
        pool.collect(
            accounts[0],
            position.tickLower,
            position.tickUpper,
            MAX_UINT128,
            MAX_UINT128,
        )

    for position in poolFixture.limitPositions:
        # TODO: This will also depend on if zeroForOne or not
        if pool.linearPositions.__contains__(
            getHashLinear(accounts[0], position.tick, position.tick == pool.token0)
        ):
            pool.burnLimitOrder(
                position.token, accounts[0], position.tick, position.liquidity
            )
            pool.collectLinear(
                accounts[0],
                position.token,
                position.tick,
                MAX_UINT128,
                MAX_UINT128,
            )


# UniswapV3Pool swap tests


@pytest.mark.usefixtures("afterEach")
def test_uniswap_swaps(TEST_POOLS):
    (_, _, pool, poolBalance0, poolBalance1, recipient, poolFixture) = TEST_POOLS
    print(poolFixture.description)

    if poolFixture.swapTests == None:
        swapTests = DEFAULT_CFPOOL_SWAP_TESTS
    else:
        swapTests = poolFixture.swapTests

    for testCase in swapTests:
        print("-------------- NEW SWAP TEST -----------")
        print("swap testCase", testCase)
        print("ticks0 before: ", pool.ticksLinearTokens0)
        print("ticks1 before: ", pool.ticksLinearTokens1)
        print("ticks RO before: ", pool.ticks)
        print("pool initial tick: ", pool.slot0.tick)

        slot0 = pool.slot0
        poolInstance = copy.deepcopy(pool)

        # Get snapshot results
        snapshotIndex = swapsSnapshot.index(
            "UniswapV3Pool swap tests "
            + poolFixture.description
            + " "
            + swapCaseToDescription(testCase)
        )
        dict = swapsSnapshot[snapshotIndex + 1]

        ######## Execute swap ########
        try:
            recipient, amount0, amount1, _, _, _ = executeSwap(
                poolInstance, testCase, recipient
            )
        except AssertionError as msg:
            assert str(msg) == "SPL"
            assert float(dict["poolBalance0"]) == pytest.approx(poolBalance0, rel=1e-12)
            assert float(dict["poolBalance1"]) == pytest.approx(poolBalance1, rel=1e-12)
            decimalPoints = decimal.Decimal(dict["poolPriceBefore"]).as_tuple().exponent
            assert float(dict["poolPriceBefore"]) == formatPriceWithPrecision(
                slot0.sqrtPriceX96, -decimalPoints
            )
            assert float(dict["tickBefore"]) == slot0.tick
            continue

        slot0After = poolInstance.slot0

        # Cannot really check balances because some positions will be burnt in some swaps
        # but not others - too cumbersome
        # Cannot really compare FeeGrowths either, because they will be split between LO and RO.
        # Mainly comparing execution prices and poolPriceAfter

        if amount0 != 0 and amount1 != 0:
            # Execution price is no longer the same as the pool price, should be abs(assetOut / assetIn).
            # To be able to compare it with uniswap ExecPrice (asset1/asset0) we calculate it the same way?
            executionPrice = -(amount1 / amount0)
        else:
            executionPrice = "-Infinity"

        print(snapshotIndex)
        print("ticks0 after: ", poolInstance.ticksLinearTokens0)
        print("ticks1 after: ", poolInstance.ticksLinearTokens1)
        print("pool final tick: ", poolInstance.slot0.tick)
        print("zeroForOne", testCase["zeroForOne"])
        print("executionPrice Uniswap", float(dict["executionPrice"]))
        decimalPoints = decimal.Decimal(dict["executionPrice"]).as_tuple().exponent
        print("executionPrice Chainflip", round(executionPrice, -decimalPoints))
        print("poolPrice Uniswap", float(dict["poolPriceAfter"]))
        decimalPoints = decimal.Decimal(dict["poolPriceAfter"]).as_tuple().exponent
        print(
            "poolPrice Chainflip",
            formatPriceWithPrecision(slot0After.sqrtPriceX96, -decimalPoints),
        )
        print("final tick Uniswap", float(dict["tickAfter"]))
        print("final tick Chainflip", slot0After.tick)

        # Allowing some very small difference due to rounding errors
        assert float(dict["amount0Before"]) == pytest.approx(poolBalance0, rel=1e-12)
        assert float(dict["amount1Before"]) == pytest.approx(poolBalance1, rel=1e-12)

        assert float(dict["tickBefore"]) == slot0.tick

        # Check that execution price is better than in only RO
        if dict["executionPrice"] in ["Infinity", "-Infinity", "NaN"]:
            assert executionPrice in ["Infinity", "-Infinity", "NaN"]

        # If it's a swap to the limit - aka can't be fulfilled
        if not testCase.__contains__("exactOut"):
            decimalPoints = decimal.Decimal(dict["poolPriceAfter"]).as_tuple().exponent
            assert float(dict["poolPriceAfter"]) == formatPriceWithPrecision(
                slot0After.sqrtPriceX96, -decimalPoints
            )
            assert float(dict["tickAfter"]) == slot0After.tick

        if poolFixture.usedLO:
            # Now execution price should always be better than the pool with noLO. PoolPrice after
            # should be the same or better, but not worse.
            if testCase["zeroForOne"]:
                if not dict["executionPrice"] in ["Infinity", "-Infinity", "NaN"]:
                    decimalPoints = (
                        decimal.Decimal(dict["executionPrice"]).as_tuple().exponent
                    )
                    assert float(dict["executionPrice"]) < round(
                        executionPrice, -decimalPoints
                    )
                if testCase.__contains__("exactOut"):
                    decimalPoints = (
                        decimal.Decimal(dict["poolPriceAfter"]).as_tuple().exponent
                    )
                    assert float(dict["poolPriceAfter"]) < formatPriceWithPrecision(
                        slot0After.sqrtPriceX96, -decimalPoints
                    )
                    assert float(dict["tickAfter"]) < slot0After.tick

            else:
                if not dict["executionPrice"] in ["Infinity", "-Infinity", "NaN"]:
                    decimalPoints = (
                        decimal.Decimal(dict["executionPrice"]).as_tuple().exponent
                    )
                    assert float(dict["executionPrice"]) > round(
                        executionPrice, -decimalPoints
                    )
                if testCase.__contains__("exactOut"):
                    decimalPoints = (
                        decimal.Decimal(dict["poolPriceAfter"]).as_tuple().exponent
                    )
                    assert float(dict["poolPriceAfter"]) > formatPriceWithPrecision(
                        slot0After.sqrtPriceX96, -decimalPoints
                    )
                    assert float(dict["tickAfter"]) > slot0After.tick
        else:
            # Now execution price should be the same than the pool with noLO
            if testCase["zeroForOne"]:
                if not dict["executionPrice"] in ["Infinity", "-Infinity", "NaN"]:
                    decimalPoints = (
                        decimal.Decimal(dict["executionPrice"]).as_tuple().exponent
                    )
                    assert float(dict["executionPrice"]) == round(
                        executionPrice, -decimalPoints
                    )
                decimalPoints = (
                    decimal.Decimal(dict["poolPriceAfter"]).as_tuple().exponent
                )
                assert float(dict["poolPriceAfter"]) == formatPriceWithPrecision(
                    slot0After.sqrtPriceX96, -decimalPoints
                )
                assert float(dict["tickAfter"]) == slot0After.tick
            else:
                if not dict["executionPrice"] in ["Infinity", "-Infinity", "NaN"]:
                    decimalPoints = (
                        decimal.Decimal(dict["executionPrice"]).as_tuple().exponent
                    )
                    assert float(dict["executionPrice"]) == round(
                        executionPrice, -decimalPoints
                    )
                if testCase.__contains__("exactOut"):
                    decimalPoints = (
                        decimal.Decimal(dict["poolPriceAfter"]).as_tuple().exponent
                    )
                    assert float(dict["poolPriceAfter"]) == formatPriceWithPrecision(
                        slot0After.sqrtPriceX96, -decimalPoints
                    )
                    assert float(dict["tickAfter"]) == slot0After.tick


def executeSwap(pool, testCase, recipient):
    sqrtPriceLimit = (
        None
        if not testCase.__contains__("sqrtPriceLimit")
        else testCase["sqrtPriceLimit"]
    )
    if testCase.__contains__("exactOut"):
        if testCase["exactOut"]:
            if testCase["zeroForOne"]:
                return swap0ForExact1(
                    pool, testCase["amount1"], recipient, sqrtPriceLimit
                )
            else:
                return swap1ForExact0(
                    pool, testCase["amount0"], recipient, sqrtPriceLimit
                )
        else:
            if testCase["zeroForOne"]:
                return swapExact0For1(
                    pool, testCase["amount0"], recipient, sqrtPriceLimit
                )
            else:
                return swapExact1For0(
                    pool, testCase["amount1"], recipient, sqrtPriceLimit
                )
    else:
        if testCase["zeroForOne"]:
            return swapToLowerPrice(pool, recipient, testCase["sqrtPriceLimit"])
        else:
            return swapToHigherPrice(pool, recipient, testCase["sqrtPriceLimit"])


def swapCaseToDescription(testCase):
    priceClause = (
        " to price " + str(formatPrice(testCase["sqrtPriceLimit"]))
        if testCase.__contains__("sqrtPriceLimit")
        else ""
    )

    if testCase.__contains__("exactOut"):
        if testCase["exactOut"]:
            if testCase["zeroForOne"]:
                return (
                    "swap token0 for exactly "
                    + formatTokenAmount(testCase["amount1"])
                    + " token1"
                    + priceClause
                )
            else:
                return (
                    "swap token1 for exactly "
                    + formatTokenAmount(testCase["amount0"])
                    + " token0"
                    + priceClause
                )
        else:
            if testCase["zeroForOne"]:
                return (
                    "swap exactly "
                    + formatTokenAmount(testCase["amount0"])
                    + " token0 for token1"
                    + priceClause
                )
            else:
                return (
                    "swap exactly "
                    + formatTokenAmount(testCase["amount1"])
                    + " token1 for token0"
                    + priceClause
                )
    else:
        if testCase["zeroForOne"]:
            return "swap token0 for token1" + priceClause
        else:
            return "swap token1 for token0" + priceClause
