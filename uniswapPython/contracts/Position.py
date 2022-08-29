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
    ## the fees owed to the position owner in token0#token1 => uint128
    tokensOwed0: int
    tokensOwed1: int


@dataclass
class PositionLinearInfo:
    ## the amount of liquidity owned by this position in the token provided
    liquidity: int
    ## percentatge swapped in the pool when the position was minted. Relative meaning.
    amountPercSwappedInsideMintedX128: int
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


def getLinear(self, owner, tick, isToken0):
    checkInputTypes(account=owner, int24=tick, bool=isToken0)

    # Need to handle non-existing positions in Python
    key = hash((owner, tick, isToken0))
    if not self.__contains__(key):
        # We don't want to create a new position if it doesn't exist!
        # In the case of collect we add an assert after that so it reverts.
        # For mint there is an amount > 0 check so it is OK to initialize
        # In burn if the position is not initialized, when calling Position.update it will revert with "NP"
        self[key] = PositionLinearInfo(0, 0, 0, 0, 0)
    return self[key]


def assertPositionExists(self, owner, tickLower, tickUpper):
    checkInputTypes(account=owner, int24=(tickLower, tickLower))
    positionInfo = get(self, owner, tickLower, tickUpper)
    assert positionInfo != PositionInfo(0, 0, 0, 0, 0), "Position doesn't exist"


def assertLimitPositionExists(self, owner, tick, isToken0):
    checkInputTypes(account=owner, int24=(tick), bool=isToken0)
    positionInfo = getLinear(self, owner, tick, isToken0)
    assert positionInfo != PositionLinearInfo(0, 0, 0, 0, 0), "Position doesn't exist"


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
    amountPercSwappedInsideX128,
    isToken0,
    pricex96,
    feeGrowthInsideX128,
):
    checkInputTypes(
        int128=(
            liquidityDelta
            # uin256=(feeGrowthInsideX128)
        ),
        uint256=(amountPercSwappedInsideX128),
        bool=(isToken0),
    )

    # If we have just created a position, we need to initialize the amountSwappedInsideLastX128.
    # We could probably do this somewhere else.
    if self == PositionLinearInfo(0, 0, 0, 0, 0):
        self.amountPercSwappedInsideMintedX128 = amountPercSwappedInsideX128
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

    # TokensOwed can be > MAX_UINT128 and < MAX_UINT256. Uniswap cast tokensOwed into uint128. This in itself
    # is an overflow and it can overflow again when adding self.tokensOwed0 += tokensOwed0. Uniswap finds this
    # acceptable to save gas. TODO: Is this OK for us?

    # Mimic Uniswap's solidity code overflow - uint128(tokensOwed0)
    if tokensOwed > MAX_UINT128:
        tokensOwed = tokensOwed & (2**128 - 1)

    # if we are burning calculate a proportional part of the position's liquidity
    # Then on the burn function we will remove them
    if liquidityDelta >= 0:
        liquidityLeftDelta = liquidityDelta
        liquiditySwappedDelta = 0
        # TODO: Think about problem when minting on top of an already minted position (same POS, same owner, same tick)
        # I think we can fix the math (update the position.amountSwappedInsideLastX128 accordingly). Might even be
        # the same math that is done in the burning, just without calculating liquidityLeftDelta and liquiditySwappedDelta.

    else:
        # TODO: Does this still work if we only burn half the position?
        # I don't think so - need to modify the self.amountPercSwappedInsideMintedX128
        # accordingly or only allow the burning of the entire postion.

        ### Calculate positionOwed (position remaining after any previous swap) regardless of the new liquidityDelta

        # amountSwappedPrev in token base (self.liquidity)
        # round up to make sure liquidityDelta doesn't become too big (in absolute numbers)
        # amountPercSwappedInsideMintedX128 + (1-amountPercSwappedInsideMintedX128) * percSwapped = amountSwappedInsideX128
        # percSwapped = (amountSwappedInsideX128 - amountPercSwappedInsideMintedX128) / (1-amountPercSwappedInsideMintedX128)
        # totalAmountSwapped = percSwapped * self.liquidity
        print(
            "DIFF", amountPercSwappedInsideX128 - self.amountPercSwappedInsideMintedX128
        )
        print(
            "self.amountPercSwappedInsideMintedX128",
            self.amountPercSwappedInsideMintedX128,
        )
        amountSwappedPrev = mulDivRoundingUp(
            toUint256(
                amountPercSwappedInsideX128 - self.amountPercSwappedInsideMintedX128
            ),
            self.liquidity,
            toUint256(FixedPoint128_Q128 - self.amountPercSwappedInsideMintedX128),
        )

        # Calculate current position ratio
        if isToken0:
            currentPosition0 = LiquidityMath.addDelta(
                self.liquidity, -amountSwappedPrev
            )
            currentPosition1 = mulDiv(amountSwappedPrev, pricex96, 2**96)

        else:
            currentPosition1 = LiquidityMath.addDelta(
                self.liquidity, -amountSwappedPrev
            )
            # Patch - there shouldn't be limit orders at the edges
            if pricex96 == 0:
                currentPosition0 = amountSwappedPrev
            else:
                currentPosition0 = mulDiv(amountSwappedPrev, 2**96, pricex96)

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

        # No need to update this. We should update this when the position is fully burnt (1)
        # but we can't burn more than that anyway, so no need to
        # self.amountPercSwappedInsideMintedX128 = amountPercSwappedInsideX128

        if isToken0:
            # Update position owed in their tokens
            self.tokensOwed0 += abs(liquidityLeftDelta)
            liquiditySwappedDelta = mulDiv(
                abs(liquiditySwappedDelta), pricex96, 2**96
            )
            self.tokensOwed1 += liquiditySwappedDelta
        else:
            liquiditySwappedDelta = mulDiv(
                abs(liquiditySwappedDelta), 2**96, pricex96
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

    # TODO: Should we clear the position if it is fully swapped?

    # Returning liquiditySwappedDelta to return as a result of the burn function
    return liquidityLeftDelta, liquiditySwappedDelta
