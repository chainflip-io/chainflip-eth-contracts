import sys, os

import LiquidityMath

sys.path.append(os.path.join(os.path.dirname(sys.path[0]), "tests"))
from utilities import *

from dataclasses import dataclass

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
    ## the fees owed to the position owner in token0#token1 => uin128
    tokensOwed0: int
    tokensOwed1: int


@dataclass
class PositionLinearInfo:
    ## the amount of liquidity owned by this position in the token provided
    liquidity: int
    ## amount swapped per unit of liquidity as of the last update to liquidity or amount swapped
    amountSwappedInsideLastX128: int
    ## the position owed to the position owner in token0#token1 => uint128
    # Since we can burn a position half swapped, we need both tokensOwed0 and tokensOwed1
    positionOwed0: int
    positionOwed1: int
    # TODO: How to keep track of the fees
    ## fee growth per unit of liquidity as of the last update to liquidity or fees owed
    feeGrowthInsideLastX128: int
    ## the fees owed to the position owner in token0#token1 => uint128
    # Since we can burn a position half swapped, we need both tokensOwed0 and tokensOwed1
    tokensOwed0: int
    tokensOwed1: int
    # Not strictly necessary since we need to pass the bool (isToken0) to generate the key
    # isToken0: bool


### @notice Returns the Info struct of a position, given an owner and position boundaries
### @param self The mapping containing all user positions
### @param owner The address of the position owner
### @param tickLower The lower tick boundary of the position
### @param tickUpper The upper tick boundary of the position
### @return position The position info struct of the given owners' position
def get(self, owner, tickLower, tickUpper):
    checkInputTypes(account=owner, int24=(tickLower, tickLower))

    # Need to handle non-existing positions in Python
    key = hash((owner, tickLower, tickUpper))
    if not self.__contains__(key):
        # We don't want to create a new position if it doesn't exist!
        # In the case of collect we add an assert after that so it reverts.
        # For mint there is an amount > 0 check so it is OK to initialize
        # In burn if the position is not initialized, when calling Position.update it will revert with "NP"
        self[key] = PositionInfo(0, 0, 0, 0, 0)
    return self[key]


def getLinear(self, owner, tick, isToken0):
    checkInputTypes(account=owner, int24=tick, bool=isToken0)

    # Need to handle non-existing positions in Python
    key = hash((owner, tick, isToken0))
    if not self.__contains__(key):
        # We don't want to create a new position if it doesn't exist!
        # In the case of collect we add an assert after that so it reverts.
        # For mint there is an amount > 0 check so it is OK to initialize
        # In burn if the position is not initialized, when calling Position.update it will revert with "NP"
        self[key] = PositionLinearInfo(0, 0, 0, 0, 0, 0, 0)
    return self[key]


def assertPositionExists(self, owner, tickLower, tickUpper):
    checkInputTypes(account=owner, int24=(tickLower, tickLower))
    positionInfo = get(self, owner, tickLower, tickUpper)
    assert positionInfo != PositionInfo(0, 0, 0, 0, 0), "Position doesn't exist"


def assertLimitPositionExists(self, owner, tick, isToken0):
    checkInputTypes(account=owner, int24=(tick), bool=isToken0)
    positionInfo = getLinear(self, owner, tick, isToken0)
    assert positionInfo != PositionLinearInfo(
        0, 0, 0, 0, 0, 0, 0
    ), "Position doesn't exist"


### @notice Credits accumulated fees to a user's position
### @param self The individual position to update
### @param liquidityDelta The change in pool liquidity as a result of the position update
### @param feeGrowthInside0X128 The all-time fee growth in token0, per unit of liquidity, inside the position's tick boundaries
### @param feeGrowthInside1X128 The all-time fee growth in token1, per unit of liquidity, inside the position's tick boundaries
def update(self, liquidityDelta, feeGrowthInside0X128, feeGrowthInside1X128):
    checkInputTypes(
        int128=(liquidityDelta), uin256=(feeGrowthInside0X128, feeGrowthInside1X128)
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

    # TokensOwed can be > MAX_UINT128 and < MAX_UINT256. Uniswap cast tokensOwed into uint128. This in itself
    # is an overflow and it can overflow again when adding self.tokensOwed0 += tokensOwed0. Uniswap finds this
    # acceptable to save gas. TODO: Is this OK for us?

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
        # TODO: Do we want to allow this overflow to happen - for now we allow it.
        ## In uniswap: overflow is acceptable, have to withdraw before you hit type(uint128).max fees
        self.tokensOwed0 += tokensOwed0
        self.tokensOwed1 += tokensOwed1


# This updates the tokensOwed (current position ratio), the position.liquidity and the fees
def updateLinear(
    self,
    liquidityDelta,
    amountSwappedInsideX128,
    isToken0,
    sqrtPricex96
    # feeGrowthInsideX128
):
    checkInputTypes(
        int128=(
            liquidityDelta
            # uin256=(feeGrowthInsideX128)
        ),
        uint256=(amountSwappedInsideX128),
        bool=(isToken0),
    )
    # If we have just created a position, we need to initialize the amountSwappedInsideLastX128.
    # We could probably do this somewhere else.
    if self == PositionLinearInfo(0, 0, 0, 0, 0, 0, 0):
        self.amountSwappedInsideLastX128 = amountSwappedInsideX128

    if liquidityDelta == 0:
        # Removed because a check is added for burn 0 uninitialized position
        # assert self.liquidity > 0, "NP"  ## disallow pokes for 0 liquidity positions
        liquidityNext = self.liquidity
    else:
        liquidityNext = LiquidityMath.addDelta(self.liquidity, liquidityDelta)

    # TODO: Add fee calculation

    # TODO: Does this make sense? If the method works for amountsSwapped then do the same
    ## calculate accumulated fees. Add toUint256 because there can be an underflow
    # tokensOwed = mulDiv(
    #     toUint256(feeGrowthInsideX128 - self.feeGrowthInsideLastX128),
    #     self.liquidity,
    #     FixedPoint128_Q128,
    # )

    # TokensOwed can be > MAX_UINT128 and < MAX_UINT256. Uniswap cast tokensOwed into uint128. This in itself
    # is an overflow and it can overflow again when adding self.tokensOwed0 += tokensOwed0. Uniswap finds this
    # acceptable to save gas. TODO: Is this OK for us?

    # Mimic Uniswap's solidity code overflow - uint128(tokensOwed0)
    # if tokensOwed > MAX_UINT128:
    #     tokensOwed = tokensOwed & (2**128 - 1)

    # In the case of mint, we only need to add liquidityDelta to LiquidityLeft. No need to update
    # anything else.
    # But in the case of burn we need to calculate the current ratio of the position and calculate
    # the amount to burn for each token. This is because the burn is position dependant (not like
    # in Uniswap where it depends on the currentPrice)
    # if we are minting
    # NOTE: Burn0 (poke) will update the fees but won't update the positionOwed, since that is dependant
    # and calculated on the amount Burnt
    if liquidityDelta >= 0:
        liquidityLeftDelta = liquidityDelta
        liquiditySwappedDelta = 0

    # if we are burning calculate a proportional part of the position's liquidity
    # Then on the burn function we will remove them
    else:
        ### Calculate positionOwed (position remaining after any previous swap) regardless of the new liquidityDelta

        # amountSwappedPrev in token base (self.liquidity)
        amountSwappedPrev = mulDiv(
            toUint256(amountSwappedInsideX128 - self.amountSwappedInsideLastX128),
            self.liquidity,
            FixedPoint128_Q128,
        )

        # Amount swapped in the actual swapped token
        if isToken0:
            currentPosition0 = LiquidityMath.addDelta(
                self.liquidity, -amountSwappedPrev
            )
            currentPosition1 = mulDiv(amountSwappedPrev, sqrtPricex96, 2**96)

        else:
            currentPosition1 = LiquidityMath.addDelta(
                self.liquidity, -amountSwappedPrev
            )
            # Patch - there shouldn't be limit orders at the edges
            if sqrtPricex96 == 0:
                currentPosition0 = amountSwappedPrev
            else:
                currentPosition0 = mulDiv(amountSwappedPrev, 2**96, sqrtPricex96)

        ### Calculate the amount of liquidity that should be burnt from liquidityLeft and liquiditySwapped

        liquidityToRemove = abs(liquidityDelta)
        # we burn a proportional part of the remaining liquidity in the tick
        # liquidityDelta / self.liquidity

        # Amount of swapped liquidity in liquidityToken (same as in tick LiquiditySwapped)
        # TODO: We should probably have tick.liquiditySwapped in tokenSwapped amount so we don't
        # need to do conversions
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

        # self.feeGrowthInsideLastX128 = feeGrowthInsideX128
        # Only update this if we have burned part or the whole position
        self.amountSwappedInsideLastX128 = amountSwappedInsideX128

        if isToken0:
            # Update position owed
            self.positionOwed0 += abs(liquidityLeftDelta)
            self.positionOwed1 += mulDiv(
                abs(liquiditySwappedDelta), sqrtPricex96, 2**96
            )
        else:
            self.positionOwed0 += mulDiv(
                abs(liquiditySwappedDelta), 2**96, sqrtPricex96
            )
            self.positionOwed1 += abs(liquidityLeftDelta)

    ## update the position
    if liquidityDelta != 0:
        self.liquidity = liquidityNext

    # Negative if we are burning. liquiditySwappedDelta in tokenSwapped
    return (liquidityLeftDelta, liquiditySwappedDelta)
