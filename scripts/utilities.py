import sys
from os import path
import traceback

import math
from dataclasses import dataclass


@dataclass
class TickInfo:
    ## the total position liquidity that references this tick
    liquidityGross: int
    ## amount of net liquidity added (subtracted) when tick is crossed from left to right (right to left),
    liquidityNet: int
    ## fee growth per unit of liquidity on the _other_ side of this tick (relative to the current tick)
    ## only has relative meaning, not absolute — the value depends on when the tick is initialized
    feeGrowthOutside0X128: int
    feeGrowthOutside1X128: int


# MAX type values
MAX_UINT128 = 2**128 - 1
MAX_UINT256 = 2**256 - 1
MAX_INT256 = 2**255 - 1
MIN_INT256 = - 2**255
MAX_UINT160 = 2**160 - 1
MIN_INT24 = - 2**24
MAX_INT24 = 2**23 - 1
MIN_INT128 = - 2**128
MAX_INT128 = 2**127 - 1
MAX_UINT8 = 2**8 - 1

TEST_TOKENS = ["TokenA", "TokenB"]

def getMinTick(tickSpacing):
    return math.ceil(-887272 / tickSpacing) * tickSpacing

def getMaxTick(tickSpacing):
    return math.floor(887272 / tickSpacing) * tickSpacing


def getMaxLiquidityPerTick(tickSpacing):
    denominator = (getMaxTick(tickSpacing) - getMinTick(tickSpacing)) // tickSpacing + 1
    return (2**128 -1)  // denominator


@dataclass
class FeeAmount:
    LOW: int = 500
    MEDIUM: int = 3000
    HIGH: int = 10000

TICK_SPACINGS = {
    FeeAmount.LOW : 10,
    FeeAmount.MEDIUM : 60,
    FeeAmount.HIGH : 200
}

def encodePriceSqrt(reserve1, reserve0):
    # Making the division by reserve0 converts it into a float which causes python to lose precision
    return int(math.sqrt(reserve1 / reserve0) * 2**96)


def expandTo18Decimals(number):
    # Converting to int because python cannot shl on a float
    return int(number * 10**18)

# @dev This function will handle reverts (aka assert failures) in the tests. However, in python there is no revert
# so we will need to handle that separately if we want to artifially revert to the previous state.
def tryExceptHandler(fcn, assertMessage, *args):
    reverted = False
    try:
        fcn(*args)
    except AssertionError as msg:
        reverted = True
        _, _, tb = sys.exc_info()
        traceback.print_tb(tb)  # Fixed format
        tb_info = traceback.extract_tb(tb)
        filename, line, func, text = tb_info[-1]

        print("An error occurred on line {} in statement {}".format(line, text))
        if str(msg) != assertMessage:
            print(
                "Reverted succesfully but not for the expected reason. \n Expected: '"
                + str(assertMessage)
                + "' but got: '"
                + str(msg)
                + "'"
            )
            assert False
        print("Succesful revert")

    if not reverted:
        print("Failed to revert: " + assertMessage)
        assert False


def checkInt128(number):
    assert number >= MIN_INT128 and number <= MAX_INT128, ''

def checkInt256(number):
    assert number >= MIN_INT256 and number <= MAX_INT256, ''

# Mimic Solidity uninitialized ticks in Python - inserting keys to an empty value in a map
def insertUninitializedTickstoMapping(mapping, keys):
    for key in keys:
        insertTickInMapping(mapping, key, TickInfo(0,0,0,0))

def insertTickInMapping(mapping,key,value):
    assert mapping.__contains__(key) == False
    mapping[key] = value

# Insert a newly initialized tick into the dictionary.
def insertInitializedTicksToMapping(mapping, keys, ticksInfo):
    assert len(keys) == len(ticksInfo)
    for i in range(len(keys)):
        insertTickInMapping(mapping,keys[i],ticksInfo[i])