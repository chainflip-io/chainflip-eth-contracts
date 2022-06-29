import sys
from os import path

sys.path.append(path.abspath("scripts"))
import Tick
import TickMath
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
    tickBitmap = None
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


def main():
    pool = UniswapPool(1, 2)
    print(pool.fee)
    r = 1
    msb = 2
    print(r, msb)
    (r, msb) = TickMath.add_bit_to_log_2(r, msb, 1, 2)
    print(r, msb)
