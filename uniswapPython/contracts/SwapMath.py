import SqrtPriceMath
from utilities import *
from decimal import *

### @title Computes the result of a swap within ticks
### @notice Contains methods for computing the result of a swap within a single tick price range, i.e., a single tick.

ONE_IN_PIPS = 1000000

### @notice Computes the result of swapping some amount in, or amount out, given the parameters of the swap
### @dev The fee, plus the amount in, will never exceed the amount remaining if the swap's `amountSpecified` is positive
### @param sqrtRatioCurrentX96 The current sqrt price of the pool
### @param sqrtRatioTargetX96 The price that cannot be exceeded, from which the direction of the swap is inferred
### @param liquidity The usable liquidity
### @param amountRemaining How much input or output amount is remaining to be swapped in#out
### @param feePips The fee taken from the input amount, expressed in hundredths of a bip
### @return sqrtRatioNextX96 The price after swapping the amount in#out, not to exceed the price target
### @return amountIn The amount to be swapped in, of either token0 or token1, based on the direction of the swap
### @return amountOut The amount to be received, of either token0 or token1, based on the direction of the swap
### @return feeAmount The amount of input that will be taken as a fee
def computeSwapStep(
    sqrtRatioCurrentX96, sqrtRatioTargetX96, liquidity, amountRemaining, feePips
):
    checkInputTypes(
        uint160=(sqrtRatioCurrentX96, sqrtRatioTargetX96),
        uint128=liquidity,
        int256=amountRemaining,
        uint24=feePips,
    )

    zeroForOne = sqrtRatioCurrentX96 >= sqrtRatioTargetX96

    # exactIn < 0 means exactOut = True
    exactIn = amountRemaining >= 0

    if exactIn:
        amountRemainingLessFee = mulDiv(
            amountRemaining, ONE_IN_PIPS - feePips, ONE_IN_PIPS
        )
        amountIn = (
            SqrtPriceMath.getAmount0Delta(
                sqrtRatioTargetX96, sqrtRatioCurrentX96, liquidity, True
            )
            if zeroForOne
            else SqrtPriceMath.getAmount1Delta(
                sqrtRatioCurrentX96, sqrtRatioTargetX96, liquidity, True
            )
        )

        if amountRemainingLessFee >= amountIn:
            sqrtRatioNextX96 = sqrtRatioTargetX96
        else:
            sqrtRatioNextX96 = SqrtPriceMath.getNextSqrtPriceFromInput(
                sqrtRatioCurrentX96, liquidity, amountRemainingLessFee, zeroForOne
            )
    else:
        amountOut = (
            SqrtPriceMath.getAmount1Delta(
                sqrtRatioTargetX96, sqrtRatioCurrentX96, liquidity, False
            )
            if zeroForOne
            else SqrtPriceMath.getAmount0Delta(
                sqrtRatioCurrentX96, sqrtRatioTargetX96, liquidity, False
            )
        )

        # amountRemaining <= 0
        if abs(amountRemaining) >= amountOut:
            sqrtRatioNextX96 = sqrtRatioTargetX96
        else:
            sqrtRatioNextX96 = SqrtPriceMath.getNextSqrtPriceFromOutput(
                sqrtRatioCurrentX96, liquidity, abs(amountRemaining), zeroForOne
            )

    max = sqrtRatioTargetX96 == sqrtRatioNextX96

    ## get the input#output amounts
    if zeroForOne:
        amountIn = (
            amountIn
            if (max and exactIn)
            else SqrtPriceMath.getAmount0Delta(
                sqrtRatioNextX96, sqrtRatioCurrentX96, liquidity, True
            )
        )
        amountOut = (
            amountOut
            if (max and not exactIn)
            else SqrtPriceMath.getAmount1Delta(
                sqrtRatioNextX96, sqrtRatioCurrentX96, liquidity, False
            )
        )

    else:
        amountIn = (
            amountIn
            if (max and exactIn)
            else SqrtPriceMath.getAmount1Delta(
                sqrtRatioCurrentX96, sqrtRatioNextX96, liquidity, True
            )
        )
        amountOut = (
            amountOut
            if (max and not exactIn)
            else SqrtPriceMath.getAmount0Delta(
                sqrtRatioCurrentX96, sqrtRatioNextX96, liquidity, False
            )
        )

    ## cap the output amount to not exceed the remaining output amount
    if (not exactIn) and (amountOut > abs(amountRemaining)):
        checkUInt256(-amountRemaining)
        amountOut = abs(amountRemaining)

    if exactIn and sqrtRatioNextX96 != sqrtRatioTargetX96:
        ## we didn't reach the target, so take the remainder of the maximum input as fee
        checkUInt256(amountRemaining)
        feeAmount = abs(amountRemaining) - amountIn
    else:
        feeAmount = mulDivRoundingUp(amountIn, feePips, ONE_IN_PIPS - feePips)

    return (sqrtRatioNextX96, amountIn, amountOut, feeAmount)


def computeLimitSwapStep(
    priceX96, liquidityGross, amountRemaining, feePips, zeroForOne, oneMinusPercSwap
):
    checkInputTypes(
        uint256=priceX96,
        uint128=liquidityGross,
        int256=amountRemaining,
        uint24=feePips,
        bool=zeroForOne,
    )
    # Calculate liquidityLeft (available) from liquidityGross and oneMinusPercSwap
    liquidity = math.floor(liquidityGross * oneMinusPercSwap)
    checkUInt128(liquidity)

    tickCrossed = False

    # exactIn < 0 means exactOut = True
    exactIn = amountRemaining >= 0

    if exactIn:
        amountRemainingLessFee = mulDiv(
            amountRemaining, ONE_IN_PIPS - feePips, ONE_IN_PIPS
        )
        if zeroForOne:
            # This might overflow - maybe to handle it differently in Rust (here we cap it afterwards)
            amountOut = SqrtPriceMath.calculateAmount1LO(
                amountRemainingLessFee, priceX96, False
            )
        else:
            amountOut = SqrtPriceMath.calculateAmount0LO(
                amountRemainingLessFee, priceX96, False
            )

        if amountOut >= liquidity:
            # Tick crossed
            if zeroForOne:
                amountIn = SqrtPriceMath.calculateAmount0LO(liquidity, priceX96, True)
            else:
                amountIn = SqrtPriceMath.calculateAmount1LO(liquidity, priceX96, True)
            assert amountIn <= amountRemainingLessFee
            resultingOneMinusPercSwap = Decimal("0")
            amountOut = liquidity

        else:
            # Tick not crossed
            amountIn, amountOut, resultingOneMinusPercSwap = calculateAmounts(amountOut,liquidity,oneMinusPercSwap, priceX96, zeroForOne)

            assert amountIn <= amountRemainingLessFee

            # NOTE: For debugging purposes, to remove.
            # Rounding difference < 1% (rounded up to 1) unless amountOut is 0.
            if amountOut != 0:
                assert abs(amountRemainingLessFee - amountIn) <= math.ceil(
                    amountRemainingLessFee / 100
                )
            else:
                assert amountIn == 0

            # Health check
            assert amountOut < liquidity

    else:
        # exactOut
        if abs(amountRemaining) >= liquidity:
            # Tick crossed
            resultingOneMinusPercSwap = Decimal("0")
            amountOut = liquidity
            if zeroForOne:
                amountIn = SqrtPriceMath.calculateAmount0LO(amountOut, priceX96, True)
            else:
                amountIn = SqrtPriceMath.calculateAmount1LO(amountOut, priceX96, True)
        else:
            # Tick not crossed
            amountIn, amountOut, resultingOneMinusPercSwap = calculateAmounts(abs(amountRemaining),liquidity,oneMinusPercSwap, priceX96, zeroForOne)

            # Health check
            assert amountOut < liquidity

    tickCrossed = amountOut == liquidity
    # Health check
    assert tickCrossed == (resultingOneMinusPercSwap == Decimal("0"))

    ## cap the output amount to not exceed the remaining output amount
    if (not exactIn) and (amountOut > abs(amountRemaining)):
        assert False, "I don't think we should get here with the CF pool"
        checkUInt256(-amountRemaining)
        amountOut = abs(amountRemaining)

    if exactIn and not tickCrossed:
        ## we didn't reach the target, so take the remainder of the maximum input as fee
        checkUInt256(amountRemaining)
        feeAmount = abs(amountRemaining) - amountIn
    else:
        feeAmount = mulDivRoundingUp(amountIn, feePips, ONE_IN_PIPS - feePips)
    return (amountIn, amountOut, feeAmount, tickCrossed, resultingOneMinusPercSwap)




def calculateAmounts(amountOut,liquidity,oneMinusPercSwap, priceX96, zeroForOne):
        # All decimal operations here are rounded down (truncated)

        # Calculate percSwapDecrease rounding down in favour of the pool (less amount out). This could maybe be rounded
        # up if end up recalculating amountIn afterwards.

        # currentPercSwapped = amountSwapped / liquidityLeft
        # tick.percSwap = tick.percSwap + (1-tick.percSwap) * currentPercSwapped128_Q128
        # tick.oneMinusPercSwap = tick.oneMinusPercSwap - tick.oneMinusPercSwap * currentPercSwapped128_Q128

        # Doing the operation in two steps because otherwise Decimal gets rounded wrongly.
        # percSwapDecrease = oneMinusPercSwap * amountOut / liquidity
        division = Decimal(amountOut) / Decimal(liquidity)
        # By default rounded down - truncated
        percSwapDecrease = oneMinusPercSwap * division

        auxPercSwapDecrease = percSwapDecrease

        # NOTE: Here is where precision is lost because oneMinusPercSwap can be 0.XYZ while percSwapDecrease can be 0.00000ZYX.
        # The precision that oneMinusPercSwap can store wil depend on how close to one it is (floating point precision).
        # We have to use the oneMinusPercSwap - initial to calculate amountIn and Out instead of percSwapDecrease because
        # precision is lost in the operation as explained above.

        # We round up the calculation to round down the percSwapDecrease
        getcontext().rounding = ROUND_UP
        resultingOneMinusPercSwap = oneMinusPercSwap - percSwapDecrease
        getcontext().rounding = ROUND_DOWN

        # Health check
        assert resultingOneMinusPercSwap > Decimal("0")
        assert resultingOneMinusPercSwap <= Decimal("1")
        # Could be equal if the amountOut/LiqLeft is many orders of magnitude smaller than oneMinusPercSwap or if it's
        # equal to zero (extreme prices)
        assert (
            resultingOneMinusPercSwap <= oneMinusPercSwap
        ), "oneMinusPercSwap should decrease or stay the same"

        # This will calculate the real percSwapDecrease that will be stored in the position. Then we use that to backcalculate
        # amount In and amount Out
        percSwapDecrease = oneMinusPercSwap - resultingOneMinusPercSwap

        # Health check
        assert abs(auxPercSwapDecrease) >= percSwapDecrease
        # To ensure amountOut it will match the burn calculation
        amountOut = SqrtPriceMath.getAmountSwappedFromTickPercentatge(
            percSwapDecrease, oneMinusPercSwap, liquidity, False
        )

        # amountIn = amountRemainingLessFee

        # Should recalculate amountIn to then take abs(amountRemaining) - amountIn as fees. There are some "issues"
        # in extreme prices (amountOut=0, amountIn=all), where if recalculated amountIn = Zero, it not recalculated
        # amountIn = All. Also, this recalculation makes amountIn potentially decrease by one, causing the fee to change.
        # This recalculation causes slight changes in amountIn which causes a change in feeAmount.

        # Recalculate amountIn from amountOut, rounding up
        if zeroForOne:
            amountIn = SqrtPriceMath.calculateAmount0LO(amountOut, priceX96, True)
        else:
            amountIn = SqrtPriceMath.calculateAmount1LO(amountOut, priceX96, True)    

        return amountIn, amountOut, resultingOneMinusPercSwap