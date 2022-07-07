from utilities import *
# from UniswapPool import *
# from Factory import *

import pytest
import Position

@dataclass
class PoolTestCase:
    description: str
    feeAmount: int
    tickSpacing: int
    startingPrice: int
    positions: list
    # SwapTestCase[]
    swapTests: list

@dataclass
class Position:
    tickLower: int
    tickUpper: int
    liquidity: int

@pytest.fixture
def pool0():
    return PoolTestCase(
        description = 'low fee, 1:1 price, 2e18 max range liquidity',
        feeAmount = FeeAmount.LOW,
        tickSpacing = TICK_SPACINGS[FeeAmount.LOW],
        startingPrice = encodePriceSqrt(1, 1),
        positions = [
        Position (
            tickLower = getMinTick(TICK_SPACINGS[FeeAmount.LOW]),
            tickUpper = getMaxTick(TICK_SPACINGS[FeeAmount.LOW]),
            liquidity = expandTo18Decimals(2),
        ),
        ],
        swapTests = None,
    )

@pytest.fixture
def pool1():
    return PoolTestCase(
        description = 'medium fee, 1:1 price, 2e18 max range liquidity',
        feeAmount = FeeAmount.MEDIUM,
        tickSpacing = TICK_SPACINGS[FeeAmount.MEDIUM],
        startingPrice = encodePriceSqrt(1, 1),
        positions = [
        Position (
            tickLower = getMinTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
            tickUpper = getMaxTick(TICK_SPACINGS[FeeAmount.MEDIUM]),
            liquidity = expandTo18Decimals(2),
        ),
        ],
        swapTests = None,
    )

# @pytest.fixture(params=[0, 1])
# def TEST_POOLS(request):
#     your_fixture = request.getfixturevalue("pool{}".format(request.param))
#     # here you can call your_fixture.do_something()
#     return your_fixture

@dataclass
class SWAP_TEST:
    zeroForOne: bool
    exactOut: bool
    amount0: int


# @pytest.fixture
# def DEFAULT_POOL_SWAP_TESTS0():
#     return SWAP_TEST(
#   ## swap large amounts in/out
#     zeroForOne = True,
#     exactOut = False,
#     amount0 = expandTo18Decimals(1),
#     )

DEFAULT_POOL_SWAP_TESTS = [{
  ## swap large amounts in/out
    "zeroForOne" : True,
    "exactOut" : False,
    "amount0" : expandTo18Decimals(1),
    },
  {
    "zeroForOne": False,
    "exactOut": False,
    "amount1": expandTo18Decimals(1),
  },
  {
    "zeroForOne": True,
    "exactOut": True,
    "amount1": expandTo18Decimals(1),
  },
  {
    "zeroForOne": False,
    "exactOut": True,
    "amount0": expandTo18Decimals(1),
  },
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
  {
    "zeroForOne": True,
    "exactOut": True,
    "amount1": expandTo18Decimals(1),
    "sqrtPriceLimit": encodePriceSqrt(50, 100),
  },
  {
    "zeroForOne": False,
    "exactOut": True,
    "amount0": expandTo18Decimals(1),
    "sqrtPriceLimit": encodePriceSqrt(200, 100),
  },
   ## swap small amounts in/out
  {
    "zeroForOne": True,
    "exactOut": False,
    "amount0": 1000,
  },
  {
    "zeroForOne": False,
    "exactOut": False,
    "amount1": 1000,
  },
  {
    "zeroForOne": True,
    "exactOut": True,
    "amount1": 1000,
  },
  {
    "zeroForOne": False,
    "exactOut": True,
    "amount0": 1000,
  },
   ## swap arbitrary input to price
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