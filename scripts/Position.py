
import LiquidityMath
import FixedPoint128
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
    ## the fees owed to the position owner in token0#token1
    tokensOwed0: int
    tokensOwed1: int




### @notice Returns the Info struct of a position, given an owner and position boundaries
### @param self The mapping containing all user positions
### @param owner The address of the position owner
### @param tickLower The lower tick boundary of the position
### @param tickUpper The upper tick boundary of the position
### @return position The position info struct of the given owners' position
def get(self,owner,tickLower,tickUpper):
    # Need to handle non-existing positions in Python
    key = hash((owner, tickLower, tickUpper))
    if not self.hasKey(key):
        # We don't want to create a new position if it doesn't exist!
            # In the case of collect we add an assert after that so it reverts. 
            # For mint there is an amount > 0 check so it is OK to initialize
            # In burn if the position is not initialized, any amount will revert. However, an amount 0 would create a position - added an assert amount > 0
        self[key] = PositionInfo(0,0,0,0,0)
    return self[key]

### @notice Credits accumulated fees to a user's position
### @param self The individual position to update
### @param liquidityDelta The change in pool liquidity as a result of the position update
### @param feeGrowthInside0X128 The all-time fee growth in token0, per unit of liquidity, inside the position's tick boundaries
### @param feeGrowthInside1X128 The all-time fee growth in token1, per unit of liquidity, inside the position's tick boundaries
def update(
    self, #PositionInfo
    liquidityDelta,
    feeGrowthInside0X128,
    feeGrowthInside1X128
):

    if (liquidityDelta == 0):
        assert self.liquidity > 0, 'NP' ## disallow pokes for 0 liquidity positions
        liquidityNext = self.liquidity
    else:
        liquidityNext = LiquidityMath.addDelta(self.liquidity, liquidityDelta)

    ## calculate accumulated fees
    tokensOwed0 = (feeGrowthInside0X128 - self.feeGrowthInside0LastX128) * self.liquidity / FixedPoint128.Q128
    tokensOwed1 = (feeGrowthInside1X128 - self.feeGrowthInside1LastX128) * self.liquidity /  FixedPoint128.Q128

    ## update the position
    if (liquidityDelta != 0): self.liquidity = liquidityNext
    self.feeGrowthInside0LastX128 = feeGrowthInside0X128
    self.feeGrowthInside1LastX128 = feeGrowthInside1X128
    if (tokensOwed0 > 0 or tokensOwed1 > 0):
        ## overflow is acceptable, have to withdraw before you hit type(uint128).max fees
        self.tokensOwed0 += tokensOwed0
        self.tokensOwed1 += tokensOwed1
