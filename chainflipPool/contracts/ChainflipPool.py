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


class ChainflipPool(UniswapPool):

    def __init__(self, token0, token1, fee, tickSpacing):
        # For now separate linear orders from uniswap range orders.
        # Also separate tick information to prevent collisions/issues when
        # clearing or updating ticks. 
        self.linearPositions = dict()
        self.ticksLinear = dict()
        
        self.linearFeeGrowthGlobal0X128 = 0
        self.linearFeeGrowthGlobal1X128 = 0

        # Pass all paramaters to UniswapPool's constructor
        super().__init__(token0, token1, fee, tickSpacing)


    def mintLinearOrder(self, token, recipient, tickLower, tickUpper, amount):
        checkInputTypes(
            string = token, accounts=(recipient), int24=(tickLower, tickUpper), uint128=(amount)
        )
        assert amount > 0
        assert token == self.token0 or token == self.token1, "Token not part of the pool"

        amountIn = self._modifyPositionLinearOrder(
            ModifyPositionParams(recipient, tickLower, tickUpper, amount)
        )

        amountIn = toUint256(abs(amountIn))

        if token == self.token0:
            recipient.transferToken(self, self.token0, amountIn)
        elif token == self.token1:
            recipient.transferToken(self, self.token1, amountIn)

        return amountIn

    def _modifyPositionLinearOrder(self,token, params):
        checkInputTypes(
            string = token,
            accounts=(params.owner),
            int24=(params.tickLower, params.tickUpper),
            int128=(params.liquidityDelta),
        )
        
        UniswapPool.checkTicks(params.tickLower, params.tickUpper)

        position = self._updatePositionLinearOrder(
            params.owner,
            params.tickLower,
            params.tickUpper,
            params.liquidityDelta,
            self.slot0.tick,
        )

        # Initialize value
        amount = 0

        if params.liquidityDelta != 0:
            # TODO: Fix/Modify this?
            if token == self.token0:
                ## Regardless of the current tick, only one asset is provided as liquidity
                amount = SqrtPriceMath.getAmount0DeltaHelper(
                    TickMath.getSqrtRatioAtTick(params.tickLower),
                    TickMath.getSqrtRatioAtTick(params.tickUpper),
                    params.liquidityDelta,
                )
            else:
                amount = SqrtPriceMath.getAmount1DeltaHelper(
                    TickMath.getSqrtRatioAtTick(params.tickLower),
                    TickMath.getSqrtRatioAtTick(params.tickUpper),
                    params.liquidityDelta,
                )

        return (position, amount)

    def _updatePositionLinearOrder(self, token, owner, tickLower, tickUpper, liquidityDelta, tick):
        checkInputTypes(
            string = token,
            accounts=(owner),
            int24=(tickLower, tickUpper, tick),
            int128=(liquidityDelta),
        )
        # This will create a position if it doesn't exist
        position = Position.getLinear(self.linearPositions, owner, tickLower, tickUpper)

        # Initialize values
        flippedLower = flippedUpper = False

        ## if we need to update the ticks, do it
        if liquidityDelta != 0:
            flippedLower = Tick.updateLinear(
                self.ticksLinear,
                tickLower,
                tick,
                liquidityDelta,
                self.linearFeeGrowthGlobal0X128,
                self.linearFeeGrowthGlobal1X128,
                False,
                self.maxLiquidityPerTick,
                token == self.token0,
            )
            flippedUpper = Tick.updateLinear(
                self.ticksLinear,
                tickUpper,
                tick,
                liquidityDelta,
                self.linearFeeGrowthGlobal0X128,
                self.linearFeeGrowthGlobal1X128,
                True,
                self.maxLiquidityPerTick,
                token == self.token0,
            )

        if flippedLower:
            assert tickLower % self.tickSpacing == 0  ## ensure that the tick is spaced
        if flippedUpper:
            assert tickUpper % self.tickSpacing == 0  ## ensure that the tick is spaced

        # TODO: Add position.feesOwed update here?? Maybe not, we can update the fees owed
        # when a swap is performed.
        
        (feeGrowthInside0X128, feeGrowthInside1X128) = Tick.getFeeGrowthInside(
            self.ticksLinear,
            tickLower,
            tickUpper,
            tick,
            self.linearFeeGrowthGlobal0X128,
            self.linearFeeGrowthGlobal1X128,
        )

        Position.update(
            position, liquidityDelta, feeGrowthInside0X128, feeGrowthInside1X128
        )

        ## clear any tick data that is no longer needed
        if liquidityDelta < 0:
            if flippedLower:
                Tick.clear(self.ticksLinear, tickLower)
            if flippedUpper:
                Tick.clear(self.ticksLinear, tickUpper)
        return position


    # Overriding UniswapPool's swap function
    def swap(self, recipient, zeroForOne, amountSpecified, sqrtPriceLimitX96):
        checkInputTypes(
            accounts=(recipient),
            bool=(zeroForOne),
            int256=(amountSpecified),
            uint160=(sqrtPriceLimitX96),
        )
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

        cache = SwapCache(feeProtocol, self.liquidity)

        exactInput = amountSpecified > 0

        state = SwapState(
            amountSpecified,
            0,
            slot0Start.sqrtPriceX96,
            slot0Start.tick,
            self.feeGrowthGlobal0X128 if zeroForOne else self.feeGrowthGlobal1X128,
            0,
            cache.liquidityStart,
        )

        while (
            state.amountSpecifiedRemaining != 0
            and state.sqrtPriceX96 != sqrtPriceLimitX96
        ):
            # For now we give priority to limit orders being executed first. In the future we might want to compare
            # and execute the one that gives a higher price. That makes things too complicatef for now.

            ######################################################
            #################### LIMIT ORDERS ####################
            ######################################################

            step = StepComputations(0, 0, 0, 0, 0, 0, 0)
            step.sqrtPriceStartX96 = state.sqrtPriceX96
            # TODO: Will we need to check the returned initialized state in case we are in the TICK MIN or TICK MAX?
            (step.tickNext, step.initialized) = UniswapPool.nextTick(self.ticksLinear, state.tick, zeroForOne)
            # Do we use the same math as in the linear pool? (aka range orders?)
            step.sqrtPriceNextX96 = TickMath.getSqrtRatioAtTick(step.tickNext)

            ## compute values to swap to the target tick, price limit, or point where input#output amount is exhausted
            if zeroForOne:
                sqrtRatioTargetX96 = (
                    sqrtPriceLimitX96
                    if step.sqrtPriceNextX96 < sqrtPriceLimitX96
                    else step.sqrtPriceNextX96
                )
                linearLiquidity = self.ticksLinear[state.tick].liquidityRangeGrossToken0
            else:
                sqrtRatioTargetX96 = (
                    sqrtPriceLimitX96
                    if step.sqrtPriceNextX96 > sqrtPriceLimitX96
                    else step.sqrtPriceNextX96
                )
                linearLiquidity = self.ticksLinear[state.tick].liquidityRangeGrossToken1
            
            (
                state.sqrtPriceX96,
                step.amountIn,
                step.amountOut,
                step.feeAmount,
            ) = SwapMath.computeSwapStep(
                state.sqrtPriceX96,
                sqrtRatioTargetX96,
                linearLiquidity,
                state.amountSpecifiedRemaining,
                self.fee,
            )

            if exactInput:
                state.amountSpecifiedRemaining -= step.amountIn + step.feeAmount
                state.amountCalculated = SafeMath.subInts(
                    state.amountCalculated, step.amountOut
                )
            else:
                state.amountSpecifiedRemaining += step.amountOut
                state.amountCalculated = SafeMath.addInts(
                    state.amountCalculated, step.amountIn + step.feeAmount
                )


            ## if the protocol fee is on, calculate how much is owed, decrement feeAmount, and increment protocolFee
            if cache.feeProtocol > 0:
                delta = abs(step.feeAmount // cache.feeProtocol)
                step.feeAmount -= delta
                state.protocolFee += delta & (2**128 - 1)


            ## shift tick if we reached the next price
            if state.sqrtPriceX96 == step.sqrtPriceNextX96:
                ## if the tick is initialized, run the tick transition
                ## @dev: here is where we should handle the case of an uninitialized boundary tick
                if step.initialized:
                    Tick.cross(
                        self.ticks,
                        step.tickNext,
                        state.feeGrowthGlobalX128
                        if zeroForOne
                        else self.feeGrowthGlobal0X128,
                        self.feeGrowthGlobal1X128
                        if zeroForOne
                        else state.feeGrowthGlobalX128,
                    )
                    # TODO: Remove all the positions included in this tick. But we can't easily get them
                    # since they keys are hashes. Store a dictionary with that??
                    
                # Do we need to update the tick here?
                state.tick = (step.tickNext - 1) if zeroForOne else step.tickNext
            elif state.sqrtPriceX96 != step.sqrtPriceStartX96:
                ## recompute unless we're on a lower tick boundary (i.e. already transitioned ticks), and haven't moved
                state.tick = TickMath.getTickAtSqrtRatio(state.sqrtPriceX96)
            
            
            # Stop the loop if the swap is completed with limit orders
            if (state.amountSpecifiedRemaining == 0 or state.sqrtPriceX96 == sqrtPriceLimitX96):
                break




            ######################################################
            #################### RANGE ORDERS ####################
            ######################################################
            step = StepComputations(0, 0, 0, 0, 0, 0, 0)
            step.sqrtPriceStartX96 = state.sqrtPriceX96
            
            # TODO: Will we need to check the returned initialized state in case we are in the TICK MIN or TICK MAX?
            (step.tickNext, step.initialized) = UniswapPool.nextTick(self.ticks, state.tick, zeroForOne)

            ## get the price for the next tick
            step.sqrtPriceNextX96 = TickMath.getSqrtRatioAtTick(step.tickNext)

            ## compute values to swap to the target tick, price limit, or point where input#output amount is exhausted
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

            if exactInput:
                state.amountSpecifiedRemaining -= step.amountIn + step.feeAmount
                state.amountCalculated = SafeMath.subInts(
                    state.amountCalculated, step.amountOut
                )
            else:
                state.amountSpecifiedRemaining += step.amountOut
                state.amountCalculated = SafeMath.addInts(
                    state.amountCalculated, step.amountIn + step.feeAmount
                )


            ## if the protocol fee is on, calculate how much is owed, decrement feeAmount, and increment protocolFee
            if cache.feeProtocol > 0:
                delta = abs(step.feeAmount // cache.feeProtocol)
                step.feeAmount -= delta
                state.protocolFee += delta & (2**128 - 1)

            ## update global fee tracker
            if state.liquidity > 0:
                state.feeGrowthGlobalX128 += mulDiv(
                    step.feeAmount, FixedPoint128_Q128, state.liquidity
                )
                # Addition can overflow in Solidity - mimic it
                state.feeGrowthGlobalX128 = toUint256(state.feeGrowthGlobalX128)

            ## shift tick if we reached the next price
            if state.sqrtPriceX96 == step.sqrtPriceNextX96:
                ## if the tick is initialized, run the tick transition
                ## @dev: here is where we should handle the case of an uninitialized boundary tick
                if step.initialized:
                    liquidityNet = Tick.cross(
                        self.ticks,
                        step.tickNext,
                        state.feeGrowthGlobalX128
                        if zeroForOne
                        else self.feeGrowthGlobal0X128,
                        self.feeGrowthGlobal1X128
                        if zeroForOne
                        else state.feeGrowthGlobalX128,
                    )
                    ## if we're moving leftward, we interpret liquidityNet as the opposite sign
                    ## safe because liquidityNet cannot be type(int128).min
                    if zeroForOne:
                        liquidityNet = -liquidityNet

                    state.liquidity = LiquidityMath.addDelta(
                        state.liquidity, liquidityNet
                    )

                state.tick = (step.tickNext - 1) if zeroForOne else step.tickNext
            elif state.sqrtPriceX96 != step.sqrtPriceStartX96:
                ## recompute unless we're on a lower tick boundary (i.e. already transitioned ticks), and haven't moved
                state.tick = TickMath.getTickAtSqrtRatio(state.sqrtPriceX96)

        ## End of swap loop
        ## update tick
        if state.tick != slot0Start.tick:
            self.slot0.sqrtPriceX96 = state.sqrtPriceX96
            self.slot0.tick = state.tick
        else:
            ## otherwise just update the price
            self.slot0.sqrtPriceX96 = state.sqrtPriceX96

        ## update liquidity if it changed
        if cache.liquidityStart != state.liquidity:
            self.liquidity = state.liquidity

        ## update fee growth global and, if necessary, protocol fees
        ## overflow is acceptable, protocol has to withdraw before it hits type(uint128).max fees

        if zeroForOne:
            self.feeGrowthGlobal0X128 = state.feeGrowthGlobalX128
            if state.protocolFee > 0:
                self.protocolFees.token0 += state.protocolFee
        else:
            self.feeGrowthGlobal1X128 = state.feeGrowthGlobalX128
            if state.protocolFee > 0:
                self.protocolFees.token1 += state.protocolFee

        (amount0, amount1) = (
            (amountSpecified - state.amountSpecifiedRemaining, state.amountCalculated)
            if (zeroForOne == exactInput)
            else (
                state.amountCalculated,
                amountSpecified - state.amountSpecifiedRemaining,
            )
        )

        ## do the transfers and collect payment
        if zeroForOne:
            if amount1 < 0:
                self.transferToken(recipient, self.token1, abs(amount1))
            balanceBefore = self.balances[self.token0]
            recipient.transferToken(self, self.token0, abs(amount0))
            assert balanceBefore + abs(amount0) == self.balances[self.token0], "IIA"
        else:
            if amount0 < 0:
                self.transferToken(recipient, self.token0, abs(amount0))

            balanceBefore = self.balances[self.token1]
            recipient.transferToken(self, self.token1, abs(amount1))
            assert balanceBefore + abs(amount1) == self.balances[self.token1], "IIA"

        return (
            recipient,
            amount0,
            amount1,
            state.sqrtPriceX96,
            state.liquidity,
            state.tick,
        )

    # TODO: Add mint, collect and burn for linear positions
