import sys, os

from utilities import *

import pytest

sys.path.append(os.path.join(os.path.dirname(sys.path[0]), "contracts"))
import Position
import TickMath


@dataclass
class poolCFTestCase:
    description: str
    feeAmount: int
    tickSpacing: int
    startingPrice: int
    positions: list
    limitPositions: list
    # SwapTestCase[]
    swapTests: list
    # whether LO will be used by the pool - This should apply to all swaps,
    # so both directions should be the same. This is to improve the checking.
    usedLO: bool


@dataclass
class Position:
    tickLower: int
    tickUpper: int
    liquidity: int


@dataclass
class PositionLimit:
    tick: int
    liquidity: int
    token: str


@pytest.fixture
def poolCF0():
    return poolCFTestCase(
        description="low fee, 1:1 price, 2e18 max range liquidity",
        feeAmount=FeeAmount.LOW,
        tickSpacing=TICK_SPACINGS[FeeAmount.LOW],
        startingPrice=encodePriceSqrt(1, 1),
        positions=[
            Position(
                tickLower=getMinTick(TICK_SPACINGS[FeeAmount.LOW]),
                tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.LOW]),
                liquidity=expandTo18Decimals(2),
            ),
        ],
        # Smaller LO positions so they get crossed by the swap when in that direction
        limitPositions=[
            PositionLimit(
                tick=0,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[0],
            ),
            PositionLimit(
                tick=0,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[1],
            ),
        ],
        swapTests=None,
        usedLO=True,
    )


# Try another pool with useless LO
@pytest.fixture
def poolCF1():
    return poolCFTestCase(
        description="low fee, 1:1 price, 2e18 max range liquidity",
        feeAmount=FeeAmount.LOW,
        tickSpacing=TICK_SPACINGS[FeeAmount.LOW],
        startingPrice=encodePriceSqrt(1, 1),
        positions=[
            Position(
                tickLower=getMinTick(TICK_SPACINGS[FeeAmount.LOW]),
                tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.LOW]),
                liquidity=expandTo18Decimals(2),
            ),
        ],
        limitPositions=[
            PositionLimit(
                tick=10000,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[0],
            ),
            PositionLimit(
                tick=-10000,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[1],
            ),
        ],
        swapTests=None,
        usedLO=False,
    )


@pytest.fixture
def poolCF2():
    return poolCFTestCase(
        description="medium fee, 1:1 price, 2e18 max range liquidity",
        feeAmount=FeeAmount.MEDIUM,
        tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
        startingPrice=encodePriceSqrt(1, 1),
        positions=[
            Position(
                tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                liquidity=expandTo18Decimals(2),
            ),
        ],
        limitPositions=[
            PositionLimit(
                tick=0,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[0],
            ),
            PositionLimit(
                tick=0,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[1],
            ),
        ],
        swapTests=None,
        usedLO=True,
    )


@pytest.fixture
def poolCF3():
    return poolCFTestCase(
        description="medium fee, 1:1 price, 2e18 max range liquidity",
        feeAmount=FeeAmount.MEDIUM,
        tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
        startingPrice=encodePriceSqrt(1, 1),
        positions=[
            Position(
                tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                liquidity=expandTo18Decimals(2),
            ),
        ],
        limitPositions=[
            PositionLimit(
                tick=10020,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[0],
            ),
            PositionLimit(
                tick=-10020,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[1],
            ),
        ],
        swapTests=None,
        usedLO=False,
    )


@pytest.fixture
def poolCF4():
    return poolCFTestCase(
        description="high fee, 1:1 price, 2e18 max range liquidity",
        feeAmount=FeeAmount.HIGH,
        tickSpacing=TICK_SPACINGS[FeeAmount.HIGH],
        startingPrice=encodePriceSqrt(1, 1),
        positions=[
            Position(
                tickLower=getMinTick(TICK_SPACINGS[FeeAmount.HIGH]),
                tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.HIGH]),
                liquidity=expandTo18Decimals(2),
            ),
        ],
        limitPositions=[
            PositionLimit(
                tick=0,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[0],
            ),
            PositionLimit(
                tick=0,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[1],
            ),
        ],
        swapTests=None,
        usedLO=True,
    )


@pytest.fixture
def poolCF5():
    return poolCFTestCase(
        description="high fee, 1:1 price, 2e18 max range liquidity",
        feeAmount=FeeAmount.HIGH,
        tickSpacing=TICK_SPACINGS[FeeAmount.HIGH],
        startingPrice=encodePriceSqrt(1, 1),
        positions=[
            Position(
                tickLower=getMinTick(TICK_SPACINGS[FeeAmount.HIGH]),
                tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.HIGH]),
                liquidity=expandTo18Decimals(2),
            ),
        ],
        limitPositions=[
            PositionLimit(
                tick=10000,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[0],
            ),
            PositionLimit(
                tick=-10000,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[1],
            ),
        ],
        swapTests=None,
        usedLO=False,
    )


# ## TODO: This is causing overflow on the math - to look into. The math in LO overflows.
# @pytest.fixture
# def poolCF6():
#     return poolCFTestCase(
#         description="medium fee, 10:1 price, 2e18 max range liquidity",
#         feeAmount=FeeAmount.MEDIUM,
#         tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
#         startingPrice=encodePriceSqrt(10, 1),
#         positions=[
#             Position(
#                 tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
#                 tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
#                 liquidity=expandTo18Decimals(2),
#             ),
#         ],
#         limitPositions=[
#             PositionLimit(
#                 # Close tick to initial tick
#                 tick=23027 - 47 ,
#                 liquidity=expandTo18Decimals(1) // 2,
#                 token=TEST_TOKENS[0],
#             ),
#             PositionLimit(
#                 # Close tick to initial tick
#                 tick=23027 - 47,
#                 liquidity=expandTo18Decimals(1) // 2,
#                 token=TEST_TOKENS[1],
#             ),
#         ],
#         swapTests=None,
#         usedLO=True,
#     )


@pytest.fixture
def poolCF7():
    return poolCFTestCase(
        description="medium fee, 10:1 price, 2e18 max range liquidity",
        feeAmount=FeeAmount.MEDIUM,
        tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
        startingPrice=encodePriceSqrt(10, 1),
        positions=[
            Position(
                tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                liquidity=expandTo18Decimals(2),
            ),
        ],
        limitPositions=[
            PositionLimit(
                # Close tick to initial tick
                tick=(23027 - 47) * 10,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[0],
            ),
            PositionLimit(
                # Close tick to initial tick
                tick=-(23027 - 47) * 10,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[1],
            ),
        ],
        swapTests=None,
        usedLO=False,
    )


# # ## TODO: This is causing overflow on the math - to look into. The math in LO overflows.
# @pytest.fixture
# def poolCF8():
#     return poolCFTestCase(
#         description="medium fee, 1:10 price, 2e18 max range liquidity",
#         feeAmount=FeeAmount.MEDIUM,
#         tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
#         startingPrice=encodePriceSqrt(1, 10),
#         positions=[
#             Position(
#                 tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
#                 tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
#                 liquidity=expandTo18Decimals(2),
#             ),
#         ],
#         limitPositions=[
#             PositionLimit(
#                 # Close tick to initial tick
#                 tick=- 23027 + 47 ,
#                 liquidity=expandTo18Decimals(1) // 2,
#                 token=TEST_TOKENS[0],
#             ),
#             PositionLimit(
#                 # Close tick to initial tick
#                 tick=-23027 + 47,
#                 liquidity=expandTo18Decimals(1) // 2,
#                 token=TEST_TOKENS[1],
#             ),
#         ],
#         swapTests=None,
#         usedLO=True,
#     )


@pytest.fixture
def poolCF9():
    return poolCFTestCase(
        description="medium fee, 1:10 price, 2e18 max range liquidity",
        feeAmount=FeeAmount.MEDIUM,
        tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
        startingPrice=encodePriceSqrt(1, 10),
        positions=[
            Position(
                tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                liquidity=expandTo18Decimals(2),
            ),
        ],
        limitPositions=[
            PositionLimit(
                tick=(-23027 + 47) * -10,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[0],
            ),
            PositionLimit(
                tick=(-23027 + 47) * 10,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[1],
            ),
        ],
        swapTests=None,
        usedLO=False,
    )


@pytest.fixture
def poolCF10():
    return poolCFTestCase(
        description="medium fee, 1:1 price, 0 liquidity, all liquidity around current price",
        feeAmount=FeeAmount.MEDIUM,
        tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
        startingPrice=encodePriceSqrt(1, 1),
        positions=[
            Position(
                tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                tickUpper=-TICK_SPACINGS[FeeAmount.MEDIUM],
                liquidity=expandTo18Decimals(2),
            ),
            Position(
                tickLower=TICK_SPACINGS[FeeAmount.MEDIUM],
                tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                liquidity=expandTo18Decimals(2),
            ),
        ],
        limitPositions=[
            PositionLimit(
                tick=0,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[0],
            ),
            PositionLimit(
                tick=0,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[1],
            ),
        ],
        swapTests=None,
        usedLO=True,
    )


@pytest.fixture
def poolCF11():
    return poolCFTestCase(
        description="medium fee, 1:1 price, 0 liquidity, all liquidity around current price",
        feeAmount=FeeAmount.MEDIUM,
        tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
        startingPrice=encodePriceSqrt(1, 1),
        positions=[
            Position(
                tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                tickUpper=-TICK_SPACINGS[FeeAmount.MEDIUM],
                liquidity=expandTo18Decimals(2),
            ),
            Position(
                tickLower=TICK_SPACINGS[FeeAmount.MEDIUM],
                tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                liquidity=expandTo18Decimals(2),
            ),
        ],
        limitPositions=[
            PositionLimit(
                tick=10020,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[0],
            ),
            PositionLimit(
                tick=-10020,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[1],
            ),
        ],
        swapTests=None,
        usedLO=False,
    )


@pytest.fixture
def poolCF12():
    return poolCFTestCase(
        description="medium fee, 1:1 price, additional liquidity around current price",
        feeAmount=FeeAmount.MEDIUM,
        tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
        startingPrice=encodePriceSqrt(1, 1),
        positions=[
            Position(
                tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                liquidity=expandTo18Decimals(2),
            ),
            Position(
                tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                tickUpper=-TICK_SPACINGS[FeeAmount.MEDIUM],
                liquidity=expandTo18Decimals(2),
            ),
            Position(
                tickLower=TICK_SPACINGS[FeeAmount.MEDIUM],
                tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                liquidity=expandTo18Decimals(2),
            ),
        ],
        limitPositions=[
            PositionLimit(
                tick=0,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[0],
            ),
            PositionLimit(
                tick=0,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[1],
            ),
        ],
        swapTests=None,
        usedLO=True,
    )


@pytest.fixture
def poolCF13():
    return poolCFTestCase(
        description="medium fee, 1:1 price, additional liquidity around current price",
        feeAmount=FeeAmount.MEDIUM,
        tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
        startingPrice=encodePriceSqrt(1, 1),
        positions=[
            Position(
                tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                liquidity=expandTo18Decimals(2),
            ),
            Position(
                tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                tickUpper=-TICK_SPACINGS[FeeAmount.MEDIUM],
                liquidity=expandTo18Decimals(2),
            ),
            Position(
                tickLower=TICK_SPACINGS[FeeAmount.MEDIUM],
                tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
                liquidity=expandTo18Decimals(2),
            ),
        ],
        limitPositions=[
            PositionLimit(
                tick=10020,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[0],
            ),
            PositionLimit(
                tick=-10020,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[1],
            ),
        ],
        swapTests=None,
        usedLO=False,
    )


# TODO: Debug this - something is a bit off with this swap
@pytest.fixture
def poolCF14():
    return poolCFTestCase(
        description="low fee, large liquidity around current price (stable swap)",
        feeAmount=FeeAmount.LOW,
        tickSpacing=TICK_SPACINGS[FeeAmount.LOW],
        startingPrice=encodePriceSqrt(1, 1),
        positions=[
            Position(
                tickLower=-TICK_SPACINGS[FeeAmount.LOW],
                tickUpper=TICK_SPACINGS[FeeAmount.LOW],
                liquidity=expandTo18Decimals(2),
            )
        ],
        limitPositions=[
            PositionLimit(
                tick=0,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[0],
            ),
            PositionLimit(
                tick=0,
                liquidity=expandTo18Decimals(1) // 2,
                token=TEST_TOKENS[1],
            ),
        ],
        swapTests=None,
        usedLO=True,
    )


# @pytest.fixture
# def poolCF8():
#     return poolCFTestCase(
#         description="medium fee, token0 liquidity only",
#         feeAmount=FeeAmount.MEDIUM,
#         tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
#         startingPrice=encodePriceSqrt(1, 1),
#         positions=[
#             Position(
#                 tickLower=0,
#                 tickUpper=2000 * TICK_SPACINGS[FeeAmount.MEDIUM],
#                 liquidity=expandTo18Decimals(2),
#             )
#         ],
#         swapTests=None,
#     )


# @pytest.fixture
# def poolCF9():
#     return poolCFTestCase(
#         description="medium fee, token1 liquidity only",
#         feeAmount=FeeAmount.MEDIUM,
#         tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
#         startingPrice=encodePriceSqrt(1, 1),
#         positions=[
#             Position(
#                 tickLower=-2000 * TICK_SPACINGS[FeeAmount.MEDIUM],
#                 tickUpper=0,
#                 liquidity=expandTo18Decimals(2),
#             )
#         ],
#         swapTests=None,
#     )


# @pytest.fixture
# def poolCF10():
#     return poolCFTestCase(
#         description="close to max price",
#         feeAmount=FeeAmount.MEDIUM,
#         tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
#         startingPrice=encodePriceSqrt(2**127, 1),
#         positions=[
#             Position(
#                 tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
#                 tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
#                 liquidity=expandTo18Decimals(2),
#             )
#         ],
#         swapTests=None,
#     )


# # This poolCF with such low starting price (or someething else) ends up with a bigger
# # than normal rounding error when comparing amount0before (and possibly others)
# @pytest.fixture
# def poolCF11():
#     return poolCFTestCase(
#         description="close to min price",
#         feeAmount=FeeAmount.MEDIUM,
#         tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
#         startingPrice=encodePriceSqrt(1, 2**127),
#         positions=[
#             Position(
#                 tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
#                 tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
#                 liquidity=expandTo18Decimals(2),
#             )
#         ],
#         swapTests=None,
#     )


# @pytest.fixture
# def poolCF12():
#     return poolCFTestCase(
#         description="max full range liquidity at 1:1 price with default fee",
#         feeAmount=FeeAmount.MEDIUM,
#         tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
#         startingPrice=encodePriceSqrt(1, 1),
#         positions=[
#             Position(
#                 tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
#                 tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
#                 liquidity=getMaxLiquidityPerTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
#             )
#         ],
#         swapTests=None,
#     )


# @pytest.fixture
# def poolCF13():
#     return poolCFTestCase(
#         description="initialized at the max ratio",
#         feeAmount=FeeAmount.MEDIUM,
#         tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
#         startingPrice=MAX_SQRT_RATIO - 1,
#         positions=[
#             Position(
#                 tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
#                 tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
#                 liquidity=expandTo18Decimals(2),
#             )
#         ],
#         swapTests=None,
#     )


# @pytest.fixture
# def poolCF14():
#     return poolCFTestCase(
#         description="initialized at the min ratio",
#         feeAmount=FeeAmount.MEDIUM,
#         tickSpacing=TICK_SPACINGS[FeeAmount.MEDIUM],
#         startingPrice=MIN_SQRT_RATIO,
#         positions=[
#             Position(
#                 tickLower=getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
#                 tickUpper=getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
#                 liquidity=expandTo18Decimals(2),
#             )
#         ],
#         swapTests=None,
#     )


@dataclass
class SWAP_TEST:
    zeroForOne: bool
    exactOut: bool
    amount0: int


DEFAULT_CFPOOL_SWAP_TESTS = [
    {
        ## swap large amounts in/out
        "zeroForOne": True,
        "exactOut": False,
        "amount0": expandTo18Decimals(1),
    },
    {
        "zeroForOne": False,
        "exactOut": False,
        "amount1": expandTo18Decimals(1),
    },
    ## NO exactOut for now
    # {
    #     "zeroForOne": True,
    #     "exactOut": True,
    #     "amount1": expandTo18Decimals(1),
    # },
    # {
    #     "zeroForOne": False,
    #     "exactOut": True,
    #     "amount0": expandTo18Decimals(1),
    # },
    ## swap large amounts in/out with a price limit
    {
        "zeroForOne": True,
        "exactOut": False,
        "amount0": expandTo18Decimals(1),
        "sqrtPriceLimit": encodePriceSqrt(50, 100),
    },
    {
        "zeroForOne": False,
        "exactOut": False,
        "amount1": expandTo18Decimals(1),
        "sqrtPriceLimit": encodePriceSqrt(200, 100),
    },
    ## NO exactOut for now
    # {
    #     "zeroForOne": True,
    #     "exactOut": True,
    #     "amount1": expandTo18Decimals(1),
    #     "sqrtPriceLimit": encodePriceSqrt(50, 100),
    # },
    # {
    #     "zeroForOne": False,
    #     "exactOut": True,
    #     "amount0": expandTo18Decimals(1),
    #     "sqrtPriceLimit": encodePriceSqrt(200, 100),
    # },
    # ## swap small amounts in/out
    # TODO: Swapping small amounts in/out can be off (e-5) - assuming it's due to rounding errors
    # Also, it is only off in extreme poolCFs, not in the ones closer to normal functioning.
    # {
    #   "zeroForOne": True,
    #   "exactOut": False,
    #   "amount0": 1000,
    # },
    # {
    #   "zeroForOne": False,
    #   "exactOut": False,
    #   "amount1": 1000,
    # },
    ## NO exactOut for now
    # {
    #     "zeroForOne": True,
    #     "exactOut": True,
    #     "amount1": 1000,
    # },
    # {
    #     "zeroForOne": False,
    #     "exactOut": True,
    #     "amount0": 1000,
    # },
    # ## swap arbitrary input to price
    {
        "sqrtPriceLimit": encodePriceSqrt(5, 2),
        "zeroForOne": False,
    },
    {
        "sqrtPriceLimit": encodePriceSqrt(2, 5),
        "zeroForOne": True,
    },
    {
        "sqrtPriceLimit": encodePriceSqrt(5, 2),
        "zeroForOne": True,
    },
    {
        "sqrtPriceLimit": encodePriceSqrt(2, 5),
        "zeroForOne": False,
    },
]
