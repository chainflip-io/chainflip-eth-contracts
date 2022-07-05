import sys
from os import path

import math

sys.path.append(path.abspath("scripts"))
from UniswapPool import *
import Tick
from utilities import *

#tickSpacingToMaxLiquidityPerTick

def test_returns_lowFee():
    print('returns the correct value for low fee')
    maxLiquidityPerTick = Tick.tickSpacingToMaxLiquidityPerTick(TICK_SPACINGS[FeeAmount.LOW])
    assert maxLiquidityPerTick == 1917569901783203986719870431555990 ##0.8 bits
    assert maxLiquidityPerTick == getMaxLiquidityPerTick(TICK_SPACINGS[FeeAmount.LOW])


def test_returns_mediumFee():
    print('returns the correct value for medium fee')
    maxLiquidityPerTick = Tick.tickSpacingToMaxLiquidityPerTick(TICK_SPACINGS[FeeAmount.MEDIUM])
    assert maxLiquidityPerTick == 11505743598341114571880798222544994  ## 113.1 bits
    assert maxLiquidityPerTick == getMaxLiquidityPerTick(TICK_SPACINGS[FeeAmount.MEDIUM])

def test_returns_highFee():
    print('returns the correct value for high fee')
    maxLiquidityPerTick = Tick.tickSpacingToMaxLiquidityPerTick(TICK_SPACINGS[FeeAmount.HIGH])
    assert maxLiquidityPerTick == 38350317471085141830651933667504588 ## 114.7 bits
    assert maxLiquidityPerTick == getMaxLiquidityPerTick(TICK_SPACINGS[FeeAmount.HIGH])

def tests_returns_allRange():
    print('returns the correct value for entire range')
    maxLiquidityPerTick = Tick.tickSpacingToMaxLiquidityPerTick(887272)
    assert maxLiquidityPerTick == MAX_UINT128 // 3 ## 126 bits
    assert maxLiquidityPerTick == getMaxLiquidityPerTick(887272)

def test_returns_for2302():
    print('returns the correct value for 2302')
    maxLiquidityPerTick = Tick.tickSpacingToMaxLiquidityPerTick(2302)
    assert maxLiquidityPerTick == 441351967472034323558203122479595605 ## 118 bits
    assert maxLiquidityPerTick == getMaxLiquidityPerTick(2302)

#getFreeGrowthInside

def test_returns_all_twoUninitialized_ifInside():
    tickMapping = {}
    insertUninitializedTickstoMapping(tickMapping, [-2, 2, 0, 15, 1])
    ( feeGrowthInside0X128, feeGrowthInside1X128 ) = Tick.getFeeGrowthInside(tickMapping,-2, 2, 0, 15, 15)
    assert feeGrowthInside0X128 == 15
    assert feeGrowthInside1X128 == 15    

def test_returns_0_twoUninitialized_ifAbove():
    tickMapping = {}
    insertUninitializedTickstoMapping(tickMapping, [-2, 2, 4, 15, 15])
    ( feeGrowthInside0X128, feeGrowthInside1X128 ) = Tick.getFeeGrowthInside(tickMapping,-2, 2, 4, 15, 15)
    assert feeGrowthInside0X128 == 0
    assert feeGrowthInside1X128 == 0

def test_returns_0_twoUninitialized_ifBelow():
    tickMapping = {}
    insertUninitializedTickstoMapping(tickMapping, [-2, 2, -4, 15, 15])
    ( feeGrowthInside0X128, feeGrowthInside1X128 ) = Tick.getFeeGrowthInside(tickMapping,-2, 2,-4, 15, 15)
    assert feeGrowthInside0X128 == 0
    assert feeGrowthInside1X128 == 0

def test_substractUpperTick_ifBelow():
    tickMapping = {}
    insertInitializedTicksToMapping(tickMapping,[2],[TickInfo(0,0,2,3)])
    insertUninitializedTickstoMapping(tickMapping, [-2, 0, 15, 15])
    ( feeGrowthInside0X128, feeGrowthInside1X128 ) = Tick.getFeeGrowthInside(tickMapping,-2, 2, 0, 15, 15)
    feeGrowthInside0X128 == 13
    feeGrowthInside1X128 == 12

def test_substractLowerTick_ifAbove():
    tickMapping = {}
    insertInitializedTicksToMapping(tickMapping,[-2],[TickInfo(0,0,2,3)])
    insertUninitializedTickstoMapping(tickMapping, [2, 0, 15, 15])
    ( feeGrowthInside0X128, feeGrowthInside1X128 ) = Tick.getFeeGrowthInside(tickMapping,-2, 2, 0, 15, 15)
    feeGrowthInside0X128 == 13
    feeGrowthInside1X128 == 12

