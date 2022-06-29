import sys
from os import path

sys.path.append(path.abspath("scripts"))
import Tick
import TickMath
import SwapMath
from dataclasses import dataclass


@dataclass
class Slot0:
    ## the current price
    sqrtPriceX96: int
    ## the current tick
    tick: int
    ## the current protocol fee as a percentage of the swap fee taken on withdrawal
    ## represented as an integer denominator (1/x)%
    feeProtocol: int


@dataclass
class ModifyPositionParams:
    ## the address that owns the position
    owner: int
    ## the lower and upper tick of the position
    tickLower: int
    tickUpper: int
    ## any change in liquidity
    liquidityDelta: int


@dataclass
class SwapCache:
    ## the protocol fee for the input token
    feeProtocol: int
    ## liquidity at the beginning of the swap
    liquidityStart: int
    ## the current value of the tick accumulator, computed only if we cross an initialized tick
    tickCumulative: int
    ## the current value of seconds per liquidity accumulator, computed only if we cross an initialized tick
    secondsPerLiquidityCumulativeX128: int
    ## whether we've computed and cached the above two accumulators
    computedLatestObservation: bool


## the top level state of the swap, the results of which are recorded in storage at the end
@dataclass
class SwapState:
    ## the amount remaining to be swapped in/out of the input/output asset
    amountSpecifiedRemaining: int
    ## the amount already swapped out/in of the output/input asset
    amountCalculated: int
    ## current sqrt(price)
    sqrtPriceX96: int
    ## the tick associated with the current price
    tick: int
    ## the global fee growth of the input token
    feeGrowthGlobalX128: int
    ## amount of input token paid as protocol fee
    protocolFee: int
    ## the current liquidity in range
    liquidity: int


@dataclass
class StepComputations:
    ## the price at the beginning of the step
    sqrtPriceStartX96: int
    ## the next tick to swap to from the current tick in the swap direction
    tickNext: int
    ## whether tickNext is initialized or not
    initialized: bool
    ## sqrt(price) for the next tick (1/0)
    sqrtPriceNextX96: int
    ## how much is being swapped in in this step
    amountIn: int
    ## how much is being swapped out
    amountOut: int
    ## how much fee is being paid in
    feeAmount: int


class UniswapPool:

    # Pool Balances
    balanceToken0 = 0
    balanceToken1 = 0

    # Class variables
    fee = None
    tickSpacing = None
    maxLiquidityPerTick = None
    slot0 = Slot0(0, 0, 0)
    feeGrowthGlobal0X128 = None
    feeGrowthGlobal1X128 = None
    protocolFees = None
    liquidity = None
    ticks = None
    tickBitmap = dict()
    positions = None

    # Constructor
    def __init__(self, fee, tickSpacing):
        self.fee = fee
        self.tickSpacing = tickSpacing
        self.maxLiquidityPerTick = Tick.tickSpacingToMaxLiquidityPerTick(tickSpacing)

    # Add transfer and receive tokens functions
    def transferTokens(self, amount0, amount1):
        self.balanceToken0 -= amount0
        self.balanceToken1 -= amount1

    def receiveTokens(self, amount0, amount1):
        self.balanceToken0 += amount0
        self.balanceToken1 += amount1

    ### @dev Common checks for valid tick inputs.
    @classmethod
    def checkTicks(tickLower, tickUpper):
        assert tickLower < tickUpper, "TLU"
        assert tickLower >= TickMath.MIN_TICK, "TLM"
        assert tickUpper <= TickMath.MAX_TICK, "TUM"

    ## Skipped `snapshotCumulativesInside`

    ### @inheritdoc IUniswapV3PoolActions
    ### @dev not locked because it initializes unlocked
    def initialize(self, sqrtPriceX96):
        assert self.slot0.sqrtPriceX96 == 0, "AI"

        tick = TickMath.getTickAtSqrtRatio(sqrtPriceX96)

        self.slot0 = Slot0(
            sqrtPriceX96,
            tick,
            0,
        )

    # TODO: implement
    # _modifyPosition , _updatePosition, mint, collect, burn,

    def swap(self, recipient, zeroForOne, amountSpecified, sqrtPriceLimitX96, data):
        assert amountSpecified != 0, "AS"

        slot0Start = self.slot0

        if zeroForOne:
            assert (
                sqrtPriceLimitX96 < slot0Start.sqrtPriceX96
                and sqrtPriceLimitX96 > TickMath.MIN_SQRT_RATIO
            ), "SPL"
        else:
            assert (
                sqrtPriceLimitX96 > slot0Start.sqrtPriceX96
                and sqrtPriceLimitX96 < TickMath.MAX_SQRT_RATIO
            ), "SPL"

        feeProtocol = (
            (slot0Start.feeProtocol % 16)
            if zeroForOne
            else (slot0Start.feeProtocol >> 4)
        )

        cache = SwapCache(self.liquidity, feeProtocol, 0, 0, False)

        exactInput = amountSpecified > 0

        feeGrowthGlobalX128 = (
            self.feeGrowthGlobal0X128 if zeroForOne else self.feeGrowthGlobal1X128
        )

        state = SwapState(
            amountSpecified,
            0,
            slot0Start.sqrtPriceX96,
            slot0Start.tick,
            feeGrowthGlobalX128,
            0,
            cache.liquidityStart,
        )

        while (
            state.amountSpecifiedRemaining != 0
            and state.sqrtPriceX96 != sqrtPriceLimitX96
        ):
            step = StepComputations()

            step.sqrtPriceStartX96 = state.sqrtPriceX96

            # TODO: Will we need to check the returned initialized state in case we are in the TICK MIN or TICK MAX?
            (step.tickNext, step.initialized) = self.nextTick(state.tick, zeroForOne)

            ## get the price for the next tick
            step.sqrtPriceNextX96 = TickMath.getSqrtRatioAtTick(step.tickNext)

            ## compute values to swap to the target tick, price limit, or point where input/output amount is exhausted
            if zeroForOne:
                sqrtRatioTargetX96 = (
                    sqrtPriceLimitX96
                    if step.sqrtPriceNextX96 < sqrtPriceLimitX96
                    else step.sqrtPriceNextX96
                )
            else:
                sqrtRatioTargetX96 = (
                    sqrtPriceLimitX96
                    if step.sqrtPriceNextX96 > sqrtPriceLimitX96
                    else step.sqrtPriceNextX96
                )

            (
                state.sqrtPriceX96,
                step.amountIn,
                step.amountOut,
                step.feeAmount,
            ) = SwapMath.computeSwapStep(
                state.sqrtPriceX96,
                sqrtRatioTargetX96,
                state.liquidity,
                state.amountSpecifiedRemaining,
                self.fee,
            )

            ## TODO: CONTINUE HERE

    # It is assumed that the keys are within [MIN_TICK , MAX_TICK]
    # TODO: Check if this is the correct direction for MAX Tick and MIN Tick
    def nextTick(self, tick, zeroForOne):
        sortedKeyList = sorted(list(self.tickBitmap.keys()))
        indexCurrentTick = sortedKeyList.index(tick)
        if zeroForOne:
            if indexCurrentTick == len(sortedKeyList) - 1:
                # No tick to the right
                return TickMath.MAX_TICK, False
            nextTick = sortedKeyList[indexCurrentTick + 1]
        else:
            if indexCurrentTick == 0:
                # No tick to the left
                return TickMath.MIN_TICK, False
            nextTick = sortedKeyList[indexCurrentTick - 1]
        return nextTick, True


def main():
    pool = UniswapPool(1, 2)
    print(pool.fee)
    r = 1
    msb = 2
    print(r, msb)
    (r, msb) = TickMath.add_bit_to_log_2(r, msb, 1, 2)
    print(r, msb)
