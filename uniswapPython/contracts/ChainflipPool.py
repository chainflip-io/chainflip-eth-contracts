import sys, os

import Tick
import TickMath
import SwapMath
import LiquidityMath
import Position
import SqrtPriceMath
import SafeMath
from UniswapPool import *

sys.path.append(os.path.join(os.path.dirname(sys.path[0]), "tests"))
from utilities import *

from dataclasses import dataclass


@dataclass
class ModifyLinearPositionParams:
    ## the address that owns the position
    owner: int
    ## the tick of the position
    tick: int
    ## any change in liquidity
    liquidityDelta: int


class ChainflipPool(UniswapPool):
    def __init__(self, token0, token1, fee, tickSpacing):
        # For now both token0 and token1 limit orders on the same mapping. Maybe we will need to keep them
        # somehow else to be able to remove them after a tick is crossed.
        self.linearPositions = dict()

        # Creating two different dicts, one for each type of limit orders (token0 and token1)
        self.ticksLinearTokens0 = dict()
        self.ticksLinearTokens1 = dict()

        # Pass all paramaters to UniswapPool's constructor
        super().__init__(token0, token1, fee, tickSpacing)

    ### @dev Common checks for valid tick inputs.
    def checkTick(tick):
        checkInputTypes(int24=(tick))
        assert tick >= TickMath.MIN_TICK, "TLM"
        assert tick <= TickMath.MAX_TICK, "TUM"

    def mintLinearOrder(self, token, recipient, tick, amount):
        checkInputTypes(
            string=token,
            accounts=(recipient),
            int24=(tick),
            uint128=(amount),
        )
        assert amount > 0
        assert (
            token == self.token0 or token == self.token1
        ), "Token not part of the pool"

        (_, amountSwappedDelta, amountLeftDelta) = self._modifyPositionLinearOrder(
            token, ModifyLinearPositionParams(recipient, tick, amount)
        )

        # Health check
        assert amountSwappedDelta == 0
        assert amountLeftDelta == amount

        amountIn = toUint256(abs(amount))

        if token == self.token0:
            recipient.transferToken(self, self.token0, amountIn)
        elif token == self.token1:
            recipient.transferToken(self, self.token1, amountIn)

        return amountIn

    def _modifyPositionLinearOrder(self, token, params):
        checkInputTypes(
            string=token,
            accounts=(params.owner),
            int24=(params.tick),
            int128=(params.liquidityDelta),
        )

        ChainflipPool.checkTick(params.tick)

        position, amountSwappedDelta, amountLeftDelta = self._updatePositionLinearOrder(
            token,
            params.owner,
            params.tick,
            params.liquidityDelta,
        )

        return (position, amountSwappedDelta, amountLeftDelta)

    def _updatePositionLinearOrder(self, token, owner, tick, liquidityDelta):
        checkInputTypes(
            string=token,
            accounts=(owner),
            int24=(tick),
            int128=(liquidityDelta),
        )
        # This will create a position if it doesn't exist
        position = Position.getLinear(
            self.linearPositions, owner, tick, token == self.token0
        )

        # Initialize values
        flipped = False
        amountSwappedDelta = amountLeftDelta = 0
        ## if we need to update the ticks, do it
        if liquidityDelta != 0:
            if token == self.token0:
                ticksLinearMap = self.ticksLinearTokens0
            else:
                ticksLinearMap = self.ticksLinearTokens1
            (flipped, amountSwappedDelta, amountLeftDelta) = Tick.updateLinear(
                ticksLinearMap,
                tick,
                liquidityDelta,
                # self.linearFeeGrowthGlobal1X128
                # if token == self.token0
                # else self.linearFeeGrowthGlobal0X128,
                self.maxLiquidityPerTick,
                # token == self.token0,
            )

        if flipped:
            assert tick % self.tickSpacing == 0  ## ensure that the tick is spaced

        # If position is token0, the fees will be in token1
        # feeGrowthInsideX128 = Tick.getFeeGrowthInsideLinear(
        #     ticksLinearMap,
        #     tickLower,
        #     tickUpper,
        #     tick,
        #     self.linearFeeGrowthGlobal1X128
        #     if token == self.token0
        #     else self.linearFeeGrowthGlobal0X128,
        # )

        Position.updateLinear(
            position,
            liquidityDelta,
            # feeGrowthInsideX128
        )

        ## clear any tick data that is no longer needed
        if liquidityDelta < 0:
            if flipped:
                Tick.clear(ticksLinearMap, tick)
        return position, amountSwappedDelta, amountLeftDelta

    # This can only be run if the tick has only been partially crossed (or not used). If fully crossed, the positions
    # will have been burnt automatically.
    def burnLimitOrder(self, token, recipient, tick, amount):
        checkInputTypes(
            string=token,
            accounts=(recipient),
            int24=(tick),
            uint128=(amount),
        )

        # Add check if the position exists - when poking an uninitialized position it can be that
        # getFeeGrowthInside finds a non-initialized tick before Position.update reverts.
        Position.assertLimitPositionExists(
            self.linearPositions, recipient, tick, token == self.token0
        )

        # Added extra recipient input variable to mimic msg.sender
        (
            position,
            amountSwappedDelta,
            amountLeftDelta,
        ) = self._modifyPositionLinearOrder(
            token,
            ModifyLinearPositionParams(recipient, tick, -amount),
        )

        (token0Delta, token1Delta) = (
            (amountLeftDelta, amountSwappedDelta)
            if token == self.token0
            else (amountSwappedDelta, amountLeftDelta)
        )

        # Mimic conversion to uint256
        amount0 = abs(-token0Delta) & (2**256 - 1)
        amount1 = abs(-token1Delta) & (2**256 - 1)

        if amount0 > 0 or amount1 > 0:
            position.tokensOwed0 += amount0
            position.tokensOwed1 += amount1

        return (recipient, tick, amount, amount)

    ### @inheritdoc IUniswapV3PoolActions
    def collectLinear(self, recipient, token, tick, amount0Requested, amount1Requested):
        checkInputTypes(
            string=token,
            accounts=(recipient),
            int24=(tick),
            uint128=(amount0Requested, amount1Requested),
        )
        # Add this check to prevent creating a new position if the position doesn't exist or it's empty
        Position.assertLimitPositionExists(
            self.linearPositions, recipient, tick, token == self.token0
        )

        ## we don't need to checkTicks here, because invalid positions will never have non-zero tokensOwed{0,1}
        ## Hardcoded recipient == msg.sender.
        position = Position.getLinear(
            self.linearPositions, recipient, tick, token == self.token0
        )

        amount0 = (
            position.tokensOwed0
            if (amount0Requested > position.tokensOwed0)
            else amount0Requested
        )
        amount1 = (
            position.tokensOwed1
            if (amount1Requested > position.tokensOwed1)
            else amount1Requested
        )

        if amount0 > 0:
            position.tokensOwed0 -= amount0
            self.transferToken(recipient, self.token0, amount0)
        if amount1 > 0:
            position.tokensOwed1 -= amount1
            self.transferToken(recipient, self.token1, amount1)

        return (recipient, tick, amount0, amount1)
