import TickMath


### @notice Derives max liquidity per tick from given tick spacing
### @dev Executed within the pool constructor
### @param tickSpacing The amount of required tick separation, realized in multiples of `tickSpacing`
###     e.g., a tickSpacing of 3 requires ticks to be initialized every 3rd tick i.e., ..., -6, -3, 0, 3, 6, ...
### @return The max liquidity per tick
def tickSpacingToMaxLiquidityPerTick(tickSpacing):
    minTick = (TickMath.MIN_TICK / tickSpacing) * tickSpacing
    maxTick = (TickMath.MAX_TICK / tickSpacing) * tickSpacing
    numTicks = ((maxTick - minTick) / tickSpacing) + 1
    return TickMath.MAX_UINT128 / numTicks
