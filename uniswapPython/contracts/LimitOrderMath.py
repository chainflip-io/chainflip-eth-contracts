import math

from decimal import *
from utilities import *


def calculateAmount1LO(amountInToken0, priceX96, roundUp):
    checkInputTypes(uint256=(priceX96), int256=amountInToken0)
    if roundUp:
        return mulDivRoundingUp(amountInToken0, priceX96, FixedPoint96_Q96)
    else:
        # We let it overflow and we will cap it afterwards - maybe to be done like computeSwapStep in Rust
        # NOTE: Not using MulDiv because of the potential overflow
        return (amountInToken0 * priceX96) // FixedPoint96_Q96


def calculateAmount0LO(amountInToken1, priceX96, roundUp):
    checkInputTypes(uint256=(priceX96), int256=amountInToken1)
    if roundUp:
        # Should never be divided by zero because it is not allowed to mint positions at price 0.
        return mulDivRoundingUp(amountInToken1, FixedPoint96_Q96, priceX96)
    else:
        # We let it overflow and we will cap it afterwards - maybe to be done like computeSwapStep in Rust
        # NOTE: Not using MulDiv because of the potential overflow
        return (amountInToken1 * FixedPoint96_Q96) // priceX96


def getAmountSwappedFromTickPercentatge(
    percSwapChange, oneMinusPercSwap, liquidityGross
):
    checkInputTypes(decimal=(percSwapChange, oneMinusPercSwap), uint128=liquidityGross)
    # By default this will be rounded down - truncated. These are Decimal types.
    perc = percSwapChange / oneMinusPercSwap
    # Conversion to integer and rounded down.
    amountSwappedPrev = math.floor(liquidityGross * perc)
    return amountSwappedPrev


# TODO: To merge this with getAmountSwappedFromTickPercentatge if the solution works
def getAmountSwappedFromTickPercentatgeRoundUp(
    percSwapChange, oneMinusPercSwap, liquidityGross
):
    checkInputTypes(decimal=(percSwapChange, oneMinusPercSwap), uint128=liquidityGross)
    setDecimalPrecRound(getcontext().prec, "ROUND_UP")
    # By default this will be rounded down - truncated. These are Decimal types.
    perc = percSwapChange / oneMinusPercSwap
    setDecimalPrecRound(getcontext().prec, "ROUND_DOWN")
    # Conversion to integer and rounded down.
    amountSwappedPrev = math.ceil(liquidityGross * perc)

    return amountSwappedPrev


def setDecimalPrecRound(precision, rounding):
    checkInputTypes(int=(precision))
    assert rounding in ["ROUND_DOWN", "ROUND_UP"]

    # Set decimal precision and rounding
    # Set all new contexts to the same default contexts
    DefaultContext.prec = precision
    DefaultContext.Emin = -999999999999999999
    DefaultContext.Emax = 999999999999999999
    DefaultContext.rounding = rounding
    setcontext(DefaultContext)


# Used only to substract percSwapDecrease from OneMinusPercSwapped. The result should never be negative.
def subtractDecimalRoundingUp(a, b):
    checkInputTypes(decimal=(a, b))
    setDecimalPrecRound(getcontext().prec, "ROUND_UP")
    result = a - b
    # Assert overflow
    assert result >= Decimal("0")
    setDecimalPrecRound(getcontext().prec, "ROUND_DOWN")
    return result
