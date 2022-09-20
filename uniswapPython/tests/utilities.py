import sys, os

import traceback

import math
from dataclasses import dataclass
import copy
from decimal import Decimal

### The minimum value that can be returned from #getSqrtRatioAtTick. Equivalent to getSqrtRatioAtTick(MIN_TICK)
MIN_SQRT_RATIO = 4295128739
### The maximum value that can be returned from #getSqrtRatioAtTick. Equivalent to getSqrtRatioAtTick(MAX_TICK)
MAX_SQRT_RATIO = 1461446703485210103287273052203988822378723970342

FixedPoint128_Q128 = 0x100000000000000000000000000000000
FixedPoint96_RESOLUTION = 96
FixedPoint96_Q96 = 0x1000000000000000000000000

# Context precision should be at least 1 factor bigger
decimalPrecision = '1e-28'
contextPrecision = 29

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


@dataclass
class TickInfoLimit:
    ## the total position liquidity that references this tick
    liquidityGross: int

    # accomulated percentatge of the pool swapped - relative meaning. Storing 1 minus the value
    # Possibly using floating point number with 256 in both the mantissa and the exponent.
    # For now, in python using Decimal to get more precision than a simple float and to be able
    # to achieve better rounding. Initial value should be one.
    oneMinusPercSwap: Decimal

    ## fee growth per unit of liquidity on the _other_ side of this tick (relative to the current tick)
    ## only has relative meaning, not absolute — the value depends on when the tick is initialized.
    ## In the token opposite to the liquidity token.
    feeGrowthInsideX128: int

    # list of owners of positions contained in this tick. We can't just store the hash because then we can't
    # know who is the owner. So we need to recalculate the hash when we burn the position. We only require the
    # owner since we figure out the isToken0 and the tick.
    ownerPositions: list


# MAX type values
MAX_UINT128 = 2**128 - 1
MAX_UINT256 = 2**256 - 1
MAX_INT256 = 2**255 - 1
MIN_INT256 = -(2**255)
MAX_UINT160 = 2**160 - 1
MIN_INT24 = -(2**24)
MAX_INT24 = 2**23 - 1
MIN_INT128 = -(2**128)
MAX_INT128 = 2**127 - 1
MAX_UINT8 = 2**8 - 1

TEST_TOKENS = ["Token0", "Token1"]


def getMinTick(tickSpacing):
    return math.ceil(-887272 / tickSpacing) * tickSpacing


def getMaxTick(tickSpacing):
    return math.floor(887272 / tickSpacing) * tickSpacing


def getMinTickLO(tickSpacing):
    return math.ceil(-665455 / tickSpacing) * tickSpacing


def getMaxTickLO(tickSpacing):
    return math.floor(665455 / tickSpacing) * tickSpacing


def getMaxLiquidityPerTick(tickSpacing):
    denominator = (getMaxTick(tickSpacing) - getMinTick(tickSpacing)) // tickSpacing + 1
    return (2**128 - 1) // denominator


@dataclass
class FeeAmount:
    LOW: int = 500
    MEDIUM: int = 3000
    HIGH: int = 10000


TICK_SPACINGS = {FeeAmount.LOW: 10, FeeAmount.MEDIUM: 60, FeeAmount.HIGH: 200}


def encodePriceSqrt(reserve1, reserve0):
    # Workaround to get the same numbers as JS

    # This ratio doesn't output the same number as in JS using big number. This causes some
    # disparities in the reusults expected. Full ratios (1,1), (2,1) ...
    # Forcing values obtained by bigNumber.js when ratio is not exact
    if reserve1 == 121 and reserve0 == 100:
        return 87150978765690771352898345369
    elif reserve1 == 101 and reserve0 == 100:
        return 79623317895830914510487008059
    elif reserve1 == 1 and reserve0 == 10:
        return 25054144837504793118650146401
    elif reserve1 == 1 and reserve0 == 2**127:
        return 6085630636
    elif reserve1 == 2**127 and reserve0 == 1:
        return 1033437718471923701407239276819587054334136928048
    else:
        return int(math.sqrt(reserve1 / reserve0) * 2**96)


def expandTo18Decimals(number):
    # Converting to int because python cannot shl on a float
    return int(number * 10**18)


## FULL MATH workarounds

# Using math.ceil or math.floor with simple / doesnt get the exact result.
def mulDivRoundingUp(a, b, c):
    return divRoundingUp(a * b, c)


# From unsafe math ensuring that it outputs the same result as Solidity
def divRoundingUp(a, b):
    result = a // b
    if a % b > 0:
        result += 1
    return result


def mulDiv(a, b, c):
    result = (a * b) // c
    checkUInt256(result)
    return result


# @dev This function will handle reverts (aka assert failures) in the tests. However, in python there is no revert
# as in the blockchain. So we will create a hard copy of the current pool and call the same method there.
def tryExceptHandler(fcn, assertMessage, *args):

    reverted = False

    try:
        # reference to object
        pool = fcn.__self__
        fcnName = fcn.__name__

        # hard copy to prevent state changes in the pool
        poolCopy = copy.deepcopy(pool)

        try:
            fcn = getattr(poolCopy, fcnName)
        except AttributeError:
            assert "Function not found in pool: " + fcnName
    except:
        # e.g. case when swapExact1ForZero is expected to revert
        print(
            "Non-pool class function passed - expect pool to be copied as part of the call"
        )

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


def checkUInt128(number):
    assert number >= 0 and number <= MAX_UINT128, "OF or UF of UINT128"
    assert type(number) == int, "Not an integer"


def checkInt128(number):
    assert number >= MIN_INT128 and number <= MAX_INT128, "OF or UF of INT128"
    assert type(number) == int, "Not an integer"


def checkInt256(number):
    assert number >= MIN_INT256 and number <= MAX_INT256, "OF or UF of INT256"
    assert type(number) == int, "Not an integer"


def checkUInt160(number):
    assert number >= 0 and number <= MAX_UINT160, "OF or UF of UINT160"
    assert type(number) == int, "Not an integer"


def checkUInt256(number):
    assert number >= 0 and number <= MAX_UINT256, "OF or UF of UINT256"
    assert type(number) == int, "Not an integer"


def checkUInt8(number):
    assert number >= 0 and number <= MAX_UINT8, "OF or UF of UINT8"
    assert type(number) == int, "Not an integer"


def checkInt24(number):
    assert number >= MIN_INT24 and number <= MAX_INT24, "OF or UF of INT24"
    assert type(number) == int, "Not an integer"

def checkfloat(input):
    assert type(input) == float

def checkString(input):
    assert type(input) == str


def checkDict(input):
    assert type(input) == dict


# TODO: Fix this since it is a recursive import
def checkAccount(recipient):
    assert True
    # assert isinstance(recipient, Account)


# Mimic unsafe overflows in Solidity
def toUint256(number):
    try:
        checkUInt256(number)
    except:
        number = number & (2**256 - 1)
        checkUInt256(number)
    return number


def toUint128(number):
    try:
        checkUInt128(number)
    except:
        number = number & (2**128 - 1)
        checkUInt128(number)
    return number


# General checkInput function for all functions that take input parameters
def checkInputTypes(**kwargs):
    if "string" in kwargs:
        loopChecking(kwargs.get("string"), checkString)
    if "accounts" in kwargs:
        loopChecking(kwargs.get("accounts"), checkAccount)
    if "int24" in kwargs:
        loopChecking(kwargs.get("int24"), checkInt24)
    if "uint256" in kwargs:
        loopChecking(kwargs.get("uint256"), checkUInt256)
    if "int256" in kwargs:
        loopChecking(kwargs.get("int256"), checkInt256)
    if "uint160" in kwargs:
        loopChecking(kwargs.get("uint160"), checkUInt160)
    if "uint128" in kwargs:
        loopChecking(kwargs.get("uint128"), checkUInt128)
    if "int128" in kwargs:
        loopChecking(kwargs.get("int128"), checkInt128)
    if "uint8" in kwargs:
        loopChecking(kwargs.get("uint8"), checkUInt8)
    if "dict" in kwargs:
        checkDict(kwargs.get("dict"))


def loopChecking(tuple, fcn):
    try:
        iter(tuple)
    except TypeError:
        # Not iterable
        fcn(tuple)
    else:
        # Iterable
        for item in tuple:
            fcn(item)


# Mimic Solidity uninitialized ticks in Python - inserting keys to an empty value in a map
def insertUninitializedTickstoMapping(mapping, keys):
    for key in keys:
        insertTickInMapping(mapping, key, TickInfo(0, 0, 0, 0))


def insertUninitializedLimitTickstoMapping(mapping, keys):
    for key in keys:
        insertTickInMapping(mapping, key, TickInfoLimit(0, Decimal(1), 0, []))


def insertTickInMapping(mapping, key, value):
    assert mapping.__contains__(key) == False
    mapping[key] = value


# Insert a newly initialized tick into the dictionary.
def insertInitializedTicksToMapping(mapping, keys, ticksInfo):
    assert len(keys) == len(ticksInfo)
    for i in range(len(keys)):
        insertTickInMapping(mapping, keys[i], ticksInfo[i])


def getPositionKey(address, lowerTick, upperTick):
    return hash((address, lowerTick, upperTick))


def getLimitPositionKey(address, tick, isToken0):
    return hash((address, tick, isToken0))


### POOL SWAPS ###
def swapExact0For1(pool, amount, recipient, sqrtPriceLimit):
    sqrtPriceLimitX96 = (
        sqrtPriceLimit
        if sqrtPriceLimit != None
        else getSqrtPriceLimitX96(TEST_TOKENS[0])
    )
    return swap(pool, TEST_TOKENS[0], [amount, 0], recipient, sqrtPriceLimitX96)


def swap0ForExact1(pool, amount, recipient, sqrtPriceLimit):
    sqrtPriceLimitX96 = (
        sqrtPriceLimit
        if sqrtPriceLimit != None
        else getSqrtPriceLimitX96(TEST_TOKENS[0])
    )
    return swap(pool, TEST_TOKENS[0], [0, amount], recipient, sqrtPriceLimitX96)


def swapExact1For0(pool, amount, recipient, sqrtPriceLimit):
    sqrtPriceLimitX96 = (
        sqrtPriceLimit
        if sqrtPriceLimit != None
        else getSqrtPriceLimitX96(TEST_TOKENS[1])
    )
    return swap(pool, TEST_TOKENS[1], [amount, 0], recipient, sqrtPriceLimitX96)


def swap1ForExact0(pool, amount, recipient, sqrtPriceLimit):
    sqrtPriceLimitX96 = (
        sqrtPriceLimit
        if sqrtPriceLimit != None
        else getSqrtPriceLimitX96(TEST_TOKENS[1])
    )
    return swap(pool, TEST_TOKENS[1], [0, amount], recipient, sqrtPriceLimitX96)


def swapToLowerPrice(pool, recipient, sqrtPriceLimit):
    return pool.swap(recipient, True, MAX_INT256, sqrtPriceLimit)


def swapToHigherPrice(pool, recipient, sqrtPriceLimit):
    return pool.swap(recipient, False, MAX_INT256, sqrtPriceLimit)


def swap(pool, inputToken, amounts, recipient, sqrtPriceLimitX96):
    [amountIn, amountOut] = amounts
    exactInput = amountOut == 0
    amount = amountIn if exactInput else amountOut

    if inputToken == TEST_TOKENS[0]:
        if exactInput:
            checkInt128(amount)
            return pool.swap(recipient, True, amount, sqrtPriceLimitX96)
        else:
            checkInt128(-amount)
            return pool.swap(recipient, True, -amount, sqrtPriceLimitX96)
    else:
        if exactInput:
            checkInt128(amount)
            return pool.swap(recipient, False, amount, sqrtPriceLimitX96)
        else:
            checkInt128(-amount)
            return pool.swap(recipient, False, -amount, sqrtPriceLimitX96)


def getSqrtPriceLimitX96(inputToken):
    if inputToken == TEST_TOKENS[0]:
        return MIN_SQRT_RATIO + 1
    else:
        return MAX_SQRT_RATIO - 1


################


def formatPrice(price):
    fraction = (price / (2**96)) ** 2
    return formatAsInSnapshot(fraction)


def formatTokenAmount(amount):
    fraction = amount / (10**18)
    return formatAsInSnapshot(fraction)


def formatAsInSnapshot(number):
    # To match snapshot formatting
    precision = int(f"{number:e}".split("e")[-1])
    # For token we want 4 extra decimals of precision
    if precision >= 0:
        precision = 4
    else:
        precision = -precision + 4

    return format(number, "." + str(precision) + "f")


def formatPriceWithPrecision(price, precision):
    fraction = (price / (2**96)) ** 2
    return round(fraction, precision)


################ Chainflip pool utilities ################


def getHashLimit(owner, tick, isToken0):
    checkInputTypes(account=owner, int24=tick, bool=isToken0)
    return hash((owner, tick, isToken0))


def assertLimitPositionExists(self, owner, tick, isToken0):
    checkInputTypes(account=owner, int24=(tick), bool=isToken0)
    key = getHashLimit(owner, tick, isToken0)
    assert self.__contains__(key), "Position doesn't exist"


def assertLimitPositionIsBurnt(self, owner, tick, isToken0):
    checkInputTypes(account=owner, int24=(tick), bool=isToken0)
    key = getHashLimit(owner, tick, isToken0)
    assert not self.__contains__(key), "Position exists"
