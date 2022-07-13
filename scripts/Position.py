import LiquidityMath
import FixedPoint128
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


### @notice Returns the Info struct of a position, given an owner and position boundaries
### @param self The mapping containing all user positions
### @param owner The address of the position owner
### @param tickLower The lower tick boundary of the position
### @param tickUpper The upper tick boundary of the position
### @return position The position info struct of the given owners' position
def get(self, owner, tickLower, tickUpper):
    # Need to handle non-existing positions in Python
    key = hash((owner, tickLower, tickUpper))
    if not self.__contains__(key):
        # We don't want to create a new position if it doesn't exist!
        # In the case of collect we add an assert after that so it reverts.
        # For mint there is an amount > 0 check so it is OK to initialize
        # In burn if the position is not initialized, when calling Position.update it will revert with "NP"
        self[key] = PositionInfo(0, 0, 0, 0, 0)
    return self[key]


### @notice Credits accumulated fees to a user's position
### @param self The individual position to update
### @param liquidityDelta The change in pool liquidity as a result of the position update
### @param feeGrowthInside0X128 The all-time fee growth in token0, per unit of liquidity, inside the position's tick boundaries
### @param feeGrowthInside1X128 The all-time fee growth in token1, per unit of liquidity, inside the position's tick boundaries
def update(self, liquidityDelta, feeGrowthInside0X128, feeGrowthInside1X128):  # PositionInfo
    # Health Check
    checkInt128(liquidityDelta)
    checkUInt256(feeGrowthInside0X128)
    checkUInt256(feeGrowthInside1X128)

    if liquidityDelta == 0:
        assert self.liquidity > 0, "NP"  ## disallow pokes for 0 liquidity positions
        liquidityNext = self.liquidity
    else:
        liquidityNext = LiquidityMath.addDelta(self.liquidity, liquidityDelta)

    ## calculate accumulated fees
    tokensOwed0 = mulDiv(
        feeGrowthInside0X128 - self.feeGrowthInside0LastX128, self.liquidity, FixedPoint128.Q128
    )
    tokensOwed1 = mulDiv(
        feeGrowthInside1X128 - self.feeGrowthInside1LastX128, self.liquidity, FixedPoint128.Q128
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
        # TODO: Do we want to allow this overflow to happen?
        ## overflow is acceptable, have to withdraw before you hit type(uint128).max fees
        self.tokensOwed0 += tokensOwed0
        self.tokensOwed1 += tokensOwed1
