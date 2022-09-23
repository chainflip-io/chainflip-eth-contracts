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
        amountRemainingLessFee = amountIn
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
        # amountRemainingLessFee = mulDiv(
        #     amountRemaining, ONE_IN_PIPS - feePips, ONE_IN_PIPS
        # )
        # For testing precision. TODO: REMOVE THIS
        amountRemainingLessFee = amountRemaining
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
            if zeroForOne:
                amountIn = SqrtPriceMath.calculateAmount0LO(liquidity, priceX96, True)
            else:
                amountIn = SqrtPriceMath.calculateAmount1LO(liquidity, priceX96, True)
            assert amountIn <= amountRemainingLessFee
            # no need to calculate percSwap Increase since we can set it to one outside this function if tickCrossed == 1
            # just initialize it
            percSwapDecrease = 1
            amountOut = liquidity

        else:
            # Tick not crossed

            # Calculate percSwapDecrease rounding down in favour of the pool (less amount out). This could maybe be rounded 
            # up if end up recalculating amountIn afterwards.

            # Doing the operation in two steps because otherwise Decimal gets rounded before quantiz.
            #percSwapDecrease = oneMinusPercSwap * amountOut / liquidity
            division = Decimal(amountOut) / Decimal(liquidity)
            print("amountOut: ", amountOut)
            print("liquidity: ", liquidity)
            # just to make the last swap very small
            if division < Decimal('0.000001'):
                division = Decimal('0.00000001')
            else:
                division = Decimal('0.00001')
            print("division: ", division)
            print("oneMinusPercSwap",oneMinusPercSwap)
            # TODO: Testing
            # By default rounded down - truncated
            percSwapDecrease = oneMinusPercSwap * division
            print("percSwapDecrease: ", percSwapDecrease)
            # percSwapDecrease = (oneMinusPercSwap * division).quantize(
            #     Decimal(decimalPrecision),
            #     rounding=ROUND_DOWN,
            #     context=Context(prec=contextPrecision),
            # )
            #print("percSwapDecrease quantized: ", percSwapDecrease)

            # To ensure amountOut it will match the burn calculation
            amountOut = SqrtPriceMath.getAmountSwappedFromTickPercentatge(
                percSwapDecrease, oneMinusPercSwap, liquidity, False
            )

            amountIn = amountRemainingLessFee
            # TODO: Should we recalculate amountIn as follows?? To then take abs(amountRemaining) - amountIn as fees. There are some "issues" in
            # extreme prices (amountOut=0, amountIn=all), where if recalculated amountIn = Zero, it not recalculated amountIn = All.
            # Recalculate amountIn from amountOut, rounding up
            # if zeroForOne:
            #     amountIn = SqrtPriceMath.calculateAmount0LO(amountOut, priceX96, True)
            # else:
            #     amountIn = SqrtPriceMath.calculateAmount1LO(amountOut, priceX96, True)
            # assert amountIn <= amountRemainingLessFee

            # Or recalculate amountIn from percSwapDecrease?

        tickCrossed = amountOut == liquidity
    else:
        assert False, "We are not handling exactOut for now"

    ## For now we just handle the exact in

    # else:
    #     # Exact out

    #     # liquidity == maxAmountOut
    #     if abs(amountRemaining) >= liquidity:
    #         amountOut = liquidity
    #     else:
    #         amountOut = abs(amountRemaining)

    # ## cap the output amount to not exceed the remaining output amount
    # if (not exactIn) and (amountOut > abs(amountRemaining)):
    #     checkUInt256(-amountRemaining)
    #     amountOut = abs(amountRemaining)

    if exactIn and not tickCrossed:
        ## we didn't reach the target, so take the remainder of the maximum input as fee
        checkUInt256(amountRemaining)
        feeAmount = abs(amountRemaining) - amountIn
    else:
        feeAmount = mulDivRoundingUp(amountIn, feePips, ONE_IN_PIPS - feePips)
    return (amountIn, amountOut, feeAmount, tickCrossed, percSwapDecrease)
