import sys, os
from venv import create

import LiquidityMath

sys.path.append(os.path.join(os.path.dirname(sys.path[0]), "tests"))
from utilities import *
import LimitOrderMath

from dataclasses import dataclass
from decimal import *

### @title Position
### @notice Positions represent an owner address' liquidity between a lower and upper tick boundary
### @dev Positions store additional state for tracking fees owed to the position


@dataclass
class PositionInfo:
    ## the amount of liquidity owned by this position
    liquidity: int
    ## fee growth per unit of liquidity as of the last update to liquidity or fees owed
    feeGrowthInside0LastX128: int
    feeGrowthInside1LastX128: int
    ## the fees owed to the position owner in token0#token1 => uint128
    tokensOwed0: int
    tokensOwed1: int


@dataclass
class PositionLimitInfo:
    ## the amount of liquidity owned by this position in the token provided
    liquidity: int
    ## percentatge swapped in the pool when the position was minted. Relative meaning.
    # Storing 1 minus the value.
    # Possibly using floating point number with 256 in both the mantissa and the exponent.
    # For now, in python using Decimal to get more precision than a simple float and to be able
    # to achieve better rounding. Initial value should be one.
    oneMinusPercSwapMint: Decimal
    ## the position owed to the position owner in token0#token1 => uint128
    # Since we can burn a position half swapped, we need both tokensOwed0 and tokensOwed1
    tokensOwed0: int
    tokensOwed1: int
    ## fee growth per unit of liquidity as of the last update to liquidity or fees owed.
    ## In the token opposite to the liquidity token.
    feeGrowthInsideLastX128: int
    # Not strictly necessary since we need to pass the bool (isToken0) to generate the key
    # isToken0: bool


### @notice Returns the Info struct of a position, given an owner and position boundaries
### @param self The mapping containing all user positions
### @param owner The address of the position owner
### @param tickLower The lower tick boundary of the position
### @param tickUpper The upper tick boundary of the position
### @return position The position info struct of the given owners' position
def get(self, owner, tickLower, tickUpper):
    checkInputTypes(account=owner, int24=(tickLower, tickUpper))

    # Need to handle non-existing positions in Python
    key = hash((owner, tickLower, tickUpper))
    if not self.__contains__(key):
        # We don't want to create a new position if it doesn't exist!
        # In the case of collect we add an assert after that so it reverts.
        # For mint there is an amount > 0 check so it is OK to initialize
        # In burn if the position is not initialized, when calling Position.update it will revert with "NP"
        self[key] = PositionInfo(0, 0, 0, 0, 0)
    return self[key]


def getLimit(self, owner, tick, isToken0):
    checkInputTypes(account=owner, int24=tick, bool=isToken0)

    # Need to handle non-existing positions in Python
    key = getHashLimit(owner, tick, isToken0)
    created = not self.__contains__(key)
    if created:
        # We don't want to create a new position if it doesn't exist!
        # In the case of collect we add an assert after that so it reverts.
        # For mint there is an amount > 0 check so it is OK to initialize
        # In burn if the position is not initialized, when calling Position.update it will revert with "NP"
        self[key] = PositionLimitInfo(0, Decimal(1), 0, 0, 0)
    return self[key], created


def assertPositionExists(self, owner, tickLower, tickUpper):
    checkInputTypes(account=owner, int24=(tickLower, tickLower))
    positionInfo = get(self, owner, tickLower, tickUpper)
    assert positionInfo != PositionInfo(0, 0, 0, 0, 0), "Position doesn't exist"
    return positionInfo


### @notice Credits accumulated fees to a user's position
### @param self The individual position to update
### @param liquidityDelta The change in pool liquidity as a result of the position update
### @param feeGrowthInside0X128 The all-time fee growth in token0, per unit of liquidity, inside the position's tick boundaries
### @param feeGrowthInside1X128 The all-time fee growth in token1, per unit of liquidity, inside the position's tick boundaries
def update(self, liquidityDelta, feeGrowthInside0X128, feeGrowthInside1X128):
    checkInputTypes(
        int128=(liquidityDelta), uint256=(feeGrowthInside0X128, feeGrowthInside1X128)
    )

    if liquidityDelta == 0:
        # Removed because a check is added for burn 0 uninitialized position
        # assert self.liquidity > 0, "NP"  ## disallow pokes for 0 liquidity positions
        liquidityNext = self.liquidity
    else:
        liquidityNext = LiquidityMath.addDelta(self.liquidity, liquidityDelta)

    ## calculate accumulated fees. Add toUint256 because there can be an underflow
    tokensOwed0 = mulDiv(
        toUint256(feeGrowthInside0X128 - self.feeGrowthInside0LastX128),
        self.liquidity,
        FixedPoint128_Q128,
    )
    tokensOwed1 = mulDiv(
        toUint256(feeGrowthInside1X128 - self.feeGrowthInside1LastX128),
        self.liquidity,
        FixedPoint128_Q128,
    )

    # NOTE: TokensOwed can be > MAX_UINT128 and < MAX_UINT256. Uniswap cast tokensOwed into uint128. This in itself
    # is an overflow and it can overflow again when adding self.tokensOwed0 += tokensOwed0. Uniswap finds this
    # acceptable to save gas. Is this OK for us?

    # Mimic Uniswap's solidity code overflow - uint128(tokensOwed0)
    if tokensOwed0 > MAX_UINT128:
        tokensOwed0 = tokensOwed0 & (2**128 - 1)
    if tokensOwed1 > MAX_UINT128:
        tokensOwed1 = tokensOwed1 & (2**128 - 1)

    ## update the position
    if liquidityDelta != 0:
        self.liquidity = liquidityNext
    self.feeGrowthInside0LastX128 = feeGrowthInside0X128
    self.feeGrowthInside1LastX128 = feeGrowthInside1X128

    if tokensOwed0 > 0 or tokensOwed1 > 0:
        # NOTE: For now we allow overflow to happen because in uniswap overflow is acceptable,
        # LPs has to withdraw before you hit type(uint128).max fees
        self.tokensOwed0 += tokensOwed0
        self.tokensOwed1 += tokensOwed1


# This updates the tokensOwed (current position ratio), the position.liquidity and the fees
def updateLimit(
    self,
    liquidityDelta,
    oneMinusPercSwap,
    isToken0,
    pricex96,
    feeGrowthInsideX128,
    created,
):
    checkInputTypes(
        int128=(liquidityDelta),
        uint256=(feeGrowthInsideX128, pricex96),
        float=oneMinusPercSwap,
        bool=(isToken0, created),
    )

    # If we have just created a position, we need to initialize the amountSwappedInsideLastX128.
    # We could probably do this somewhere else.
    if created:
        assert liquidityDelta > 0  # health check
        self.oneMinusPercSwapMint = oneMinusPercSwap
        self.feegrowthInsideLastX128 = feeGrowthInsideX128

    if liquidityDelta == 0:
        # Removed because a check is added for burn 0 uninitialized position
        # assert self.liquidity > 0, "NP"  ## disallow pokes for 0 liquidity positions
        liquidityNext = self.liquidity
    else:
        liquidityNext = LiquidityMath.addDelta(self.liquidity, liquidityDelta)

    # TokensOwed is not in liquidity token
    tokensOwed = mulDiv(
        toUint256(feeGrowthInsideX128 - self.feeGrowthInsideLastX128),
        self.liquidity,
        FixedPoint128_Q128,
    )

    # NOTE: TokensOwed can be > MAX_UINT128 and < MAX_UINT256. Uniswap cast tokensOwed into uint128. This in itself
    # is an overflow and it can overflow again when adding self.tokensOwed0 += tokensOwed0. Uniswap finds this
    # acceptable to save gas. Is this OK for us?

    # Mimic Uniswap's solidity code overflow - uint128(tokensOwed0)
    if tokensOwed > MAX_UINT128:
        tokensOwed = tokensOwed & (2**128 - 1)

    # if we are burning calculate a proportional part of the position's liquidity
    # Then on the burn function we will remove them
    if liquidityDelta >= 0:
        liquidityLeftDelta = liquidityDelta
        liquiditySwappedDelta = 0
        # If there has been any swap in this position before this mint, recompute the oneMinusPercSwap.
        if liquidityDelta > 0 and oneMinusPercSwap < self.oneMinusPercSwapMint:

            # newOneMinusPercSwapMint should be rounded up. Looking at the math, we need amountSwappedPrev to be rounded down

            # We round up the calculation to round down the percSwapDecrease
            percSwapDecrease = self.oneMinusPercSwapMint - oneMinusPercSwap

            amountSwappedPrev = LimitOrderMath.getAmountSwappedFromTickPercentatge(
                percSwapDecrease,
                self.oneMinusPercSwapMint,
                self.liquidity,
            )

            # amountSwappedPrev = math.floor(
            #     # percSwap - percSwapMint === (1 - percSwapMint) - (1 - percSwap)
            #     (self.oneMinusPercSwapMint - oneMinusPercSwap) * self.liquidity / self.oneMinusPercSwapMint
            # )
            # When burnt the next time, the calculation will be like explained below. So we need to modify the
            # self.percSwapMint so with the new liquidity we get the same amount swapped.

            # amountSwappedPrev = mulDivRoundingUp(
            #           percSwap - self.percSwapMint),
            #           self.liquidity,
            #           toUint256(FixedPoint128_Q128 - self.percSwapMint),
            # )  == mulDivRoundingUp(
            #           percSwap - X,
            #           liquidityNext,
            #           FixedPoint128_Q128 - X,
            # )

            # Resolving for X ( X === newly minted percentatge to be stored in the postion -> self.percSwapMint)
            # X = ((liquidityNext * percSwap) -  (amountSwappedPrev * FixedPoint128_Q128))/(liquidityNext - amountSwappedPrev)

            # Denonimator cannot be <=0 given that:
            # liquidityNext > amountSwappedPrev, since amountSwappedPrev is in the same currency as liquidity and liquidityNext > liquidity.
            # Numerator cannot be <= 0:
            # liquidityNext * percSwap > amountSwappedPrev * FixedPoint128_Q128
            # Left term would give is the maximum amount (upper limit) that might have been swapped in the pool including new liquidity.
            # On the right, the amount swapped of that same token before this new mint. Amount swapped before cannot be bigger than the
            # max amount swapped including new liquidity.

            # TODO: Alastair mentioned this potentially being able to be calculated in a simpler way. To discuss.

            # Round percSwap down which means rounding substrahend down and newOneMinusPercSwapMint up.
            substrahend = (
                liquidityNext * (1 - oneMinusPercSwap) - amountSwappedPrev
            ) / (liquidityNext - amountSwappedPrev)
            newOneMinusPercSwapMint = LimitOrderMath.subtractDecimalRoundingUp(
                Decimal("1"), substrahend
            )

            # Health checks
            assert newOneMinusPercSwapMint < self.oneMinusPercSwapMint
            assert newOneMinusPercSwapMint > oneMinusPercSwap
            assert newOneMinusPercSwapMint > 0

            self.oneMinusPercSwapMint = newOneMinusPercSwapMint

    else:
        ### Calculate positionOwed (position remaining after any previous swap) regardless of the new liquidityDelta

        # Current pool percSwap is adjusted (not absolute number) so we need to reverse engineer it to get the position's swap%.
        # We know in swap, the new percSwap gets calculated like this:
        # tick.percSwap = tick.percSwap + (1-tick.percSwap) * currentPercSwapped128_Q128
        # We know that when the position was minted, percSwap == self.percSwapMint
        # So we need to calculate the average % swapped in the tick after mint - will equate to currentPercSwap in the previous formula
        # That should encapsulate the average of all swaps performed after that.
        # percSwap = self.percSwapMint + (1-self.percSwapMint) * percSwappedAfterMint
        # percSwappedAfterMint = (percSwap - self.percSwapMint) / (1-self.percSwapMint)
        # totalAmountSwapped = percSwappedAfterMint * self.liquidity

        # percSwap - percSwapMint === (1 - percSwapMint) - (1 - percSwap)
        assert self.oneMinusPercSwapMint > 0

        # We round down the calculation
        percSwapDecrease = self.oneMinusPercSwapMint - oneMinusPercSwap

        amountSwappedPrev = LimitOrderMath.getAmountSwappedFromTickPercentatge(
            percSwapDecrease,
            self.oneMinusPercSwapMint,
            self.liquidity,
        )

        # Same issue as in SwapMath
        amountSwappedPrevRounding = (
            LimitOrderMath.getAmountSwappedFromTickPercentatgeRoundUp(
                percSwapDecrease,
                self.oneMinusPercSwapMint,
                self.liquidity,
            )
        )

        # Calculate current position ratio
        if isToken0:
            currentPosition0 = LiquidityMath.addDelta(
                self.liquidity, -amountSwappedPrevRounding
            )
            currentPosition1 = LimitOrderMath.calculateAmount1LO(
                amountSwappedPrev, pricex96, False
            )

        else:
            currentPosition1 = LiquidityMath.addDelta(
                self.liquidity, -amountSwappedPrevRounding
            )
            currentPosition0 = LimitOrderMath.calculateAmount0LO(
                amountSwappedPrev, pricex96, False
            )

        ### Calculate the amount of liquidity that should be burnt from liquidityLeft and liquiditySwapped

        liquidityToRemove = abs(liquidityDelta)
        # we burn a proportional part of the remaining liquidity in the tick
        # liquidityDelta / self.liquidity

        # Amount of swapped liquidity in liquidity Token
        liquiditySwappedDelta = -mulDiv(
            liquidityToRemove, amountSwappedPrev, self.liquidity
        )
        if isToken0:
            liquidityLeftDelta = -mulDiv(
                liquidityToRemove, currentPosition0, self.liquidity
            )
        else:
            liquidityLeftDelta = -mulDiv(
                liquidityToRemove, currentPosition1, self.liquidity
            )
        # Mimic Uniswap's solidity code overflow - uint128(tokensOwed0)
        if currentPosition0 > MAX_UINT128:
            currentPosition0 = currentPosition0 & (2**128 - 1)
        if currentPosition1 > MAX_UINT128:
            currentPosition1 = currentPosition1 & (2**128 - 1)

        # No need to update oneMinusPercSwapMint. We should update this
        # when the position is fully burnt (1) but we can't burn more than that anyway,
        # so no need to self.oneMinusPercSwapMint = oneMinusPercSwap

        if isToken0:
            # Update position owed in their tokens
            self.tokensOwed0 += abs(liquidityLeftDelta)
            liquiditySwappedDelta = LimitOrderMath.calculateAmount1LO(
                abs(liquiditySwappedDelta), pricex96, False
            )
            self.tokensOwed1 += liquiditySwappedDelta
        else:
            liquiditySwappedDelta = LimitOrderMath.calculateAmount0LO(
                abs(liquiditySwappedDelta), pricex96, False
            )
            self.tokensOwed0 += liquiditySwappedDelta
            self.tokensOwed1 += abs(liquidityLeftDelta)

    ## update the position
    if liquidityDelta != 0:
        self.liquidity = liquidityNext

    # Update position fees
    self.feeGrowthInsideLastX128 = feeGrowthInsideX128

    # Add token fees to the position (added to burnt tokens if we are burning)
    # TokensOwed is not in liquidity token
    if tokensOwed > 0:
        if isToken0:
            self.tokensOwed1 += tokensOwed
        else:
            self.tokensOwed0 += tokensOwed

    # Returning liquiditySwappedDelta to return as a result of the burn function
    return liquidityLeftDelta, liquiditySwappedDelta
