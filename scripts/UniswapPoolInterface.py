import sys
from os import path


sys.path.append(path.abspath("scripts"))
import UniswapPool
from utilities import *

# Adding all the typecheck on top of each function to catch potential issues
class UniswapPoolInterface(UniswapPool):


    # Constructor
    def __init__(self, token0, token1, fee, tickSpacing):
        checkInputTypes(string=(token0,token1))
        return super().__init__(token0, token1, fee, tickSpacing)


    def checkTicks(tickLower, tickUpper):
        checkInputTypes(int24=(tickLower, tickUpper))
        return super().checkTicks(tickLower, tickUpper)

    def initialize(self, sqrtPriceX96):
        checkInputTypes(uint160=(sqrtPriceX96))
        return super().initialize(sqrtPriceX96)

    def _modifyPosition(self, params):
        checkInputTypes(string=(params.owner),int24=(params.tickLower, params.tickUpper),int128=(params.liquidityDelta))
        return super()._modifyPosition(params)

    def _updatePosition(self, owner, tickLower, tickUpper, liquidityDelta, tick):
        checkInputTypes(string=(owner),int24=(tickLower, tickUpper, tick),int128=(liquidityDelta))
        return super()._updatePosition(owner, tickLower, tickUpper, liquidityDelta, tick)
        
    def mint(self, recipient, tickLower, tickUpper, amount):
        checkInputTypes(string=(recipient),int24=(tickLower, tickUpper),uint128=(amount))
        return super().mint(recipient, tickLower, tickUpper, amount)

    def collect(
        self, recipient, tickLower, tickUpper, amount0Requested, amount1Requested
    ):
        checkInputTypes(string=(recipient),int24=(tickLower, tickUpper),uint128=(amount0Requested, amount1Requested))
        return super().collect(recipient, tickLower, tickUpper, amount0Requested, amount1Requested)

    

    def burn(self, recipient, tickLower, tickUpper, amount):
        checkInputTypes(string=(recipient),int24=(tickLower, tickUpper),uint128=(amount))
        return super().burn(recipient, tickLower, tickUpper, amount)

    def swap(self, recipient, zeroForOne, amountSpecified, sqrtPriceLimitX96):
        checkInputTypes(string=(recipient),bool=(zeroForOne),uint256=(amountSpecified),uint160=(sqrtPriceLimitX96))
        return super().swap(recipient, zeroForOne, amountSpecified, sqrtPriceLimitX96)

    def setFeeProtocol(self, feeProtocol0, feeProtocol1):
        checkInputTypes(uint8=(feeProtocol0, feeProtocol1))
        return super().setFeeProtocol(feeProtocol0, feeProtocol1)

    def collectProtocol(self, recipient, amount0Requested, amount1Requested):
        checkInputTypes(string=(recipient),uint128=(amount0Requested, amount1Requested))

    # It is assumed that the keys are within [MIN_TICK , MAX_TICK]
    # We don't run the risk of overshooting tickNext (out of boundaries) as long as ticks (keys) have been initialized
    # within the boundaries. However, if there is no initialized tick to the left or right we will return the next boundary
    # Then we need to return the initialized bool to indicate that we are at the boundary and it is not an initalized tick.
    ### @param self The mapping in which to compute the next initialized tick
    ### @param tick The starting tick
    ### @param tickSpacing The spacing between usable ticks
    ### @param lte Whether to search for the next initialized tick to the left (less than or equal to the starting tick)
    ### @return next The next initialized or uninitialized tick => int24
    ### @return initialized Whether the next tick is initialized to signal if we have reached an initialized boundary

    def nextTick(self, tick, lte):
        if not self.ticks.__contains__(tick):
            # If tick doesn't exist in the mapping we fake it (easier than searching for nearest value)
            sortedKeyList = sorted(list(self.ticks.keys()) + [tick])
        else:
            sortedKeyList = sorted(list(self.ticks.keys()))

        indexCurrentTick = sortedKeyList.index(tick)

        if lte:
            # If the current tick is initialized (not faked), we return the current tick
            if self.ticks.__contains__(tick):
                return tick, True
            elif indexCurrentTick == 0:
                # No tick to the left
                return TickMath.MIN_TICK, False
            else:
                nextTick = sortedKeyList[indexCurrentTick - 1]
        else:

            if indexCurrentTick == len(sortedKeyList) - 1:
                # No tick to the right
                return TickMath.MAX_TICK, False
            nextTick = sortedKeyList[indexCurrentTick + 1]

        # Return tick within the boundaries
        return nextTick, True
