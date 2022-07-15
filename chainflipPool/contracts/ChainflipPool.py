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

        self.liquidityLinear = 0

        # Creating two different dicts, one for each type of limit orders (token0 and token1)
        self.ticksLinearTokens0 = dict()
        self.ticksLinearTokens1 = dict()

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

        (_,amountIn) = self._modifyPositionLinearOrder( token,
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

        # Initialize value
        amount = 0

        position = self._updatePositionLinearOrder(
            token,
            params.owner,
            params.tickLower,
            params.tickUpper,
            params.liquidityDelta,
            self.slot0.tick,
        )

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
            if self.slot0.tick >= params.tickUpper and self.slot0.tick < params.tickUpper:
                self.liquidityLinear = LiquidityMath.addDelta(self.liquidityLinear, params.liquidityDelta)

        return (position, amount)

    def _updatePositionLinearOrder(self, token, owner, tickLower, tickUpper, liquidityDelta, tick):
        checkInputTypes(
            string = token,
            accounts=(owner),
            int24=(tickLower, tickUpper, tick),
            int128=(liquidityDelta),
        )
        # This will create a position if it doesn't exist
        position = Position.getLinear(self.linearPositions, owner, tickLower, tickUpper, token == self.token0)

        # Initialize values
        flippedLower = flippedUpper = False

        ## if we need to update the ticks, do it
        if liquidityDelta != 0:
            if token == token:
                ticksLinearMap = self.ticksLinearTokens0
            else:
                ticksLinearMap = self.ticksLinearTokens1
            flippedLower = Tick.updateLinear(
                ticksLinearMap,
                tickLower,
                tick,
                liquidityDelta,
                self.linearFeeGrowthGlobal0X128 if token== self.token0 else self.linearFeeGrowthGlobal1X128,
                False,
                self.maxLiquidityPerTick,
                token == self.token0,
            )
            flippedUpper = Tick.updateLinear(
                ticksLinearMap,
                tickUpper,
                tick,
                liquidityDelta,
                self.linearFeeGrowthGlobal1X128 if token== self.token0 else self.linearFeeGrowthGlobal0X128,
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
        
        feeGrowthInsideX128 = Tick.getFeeGrowthInsideLinear(
            ticksLinearMap,
            tickLower,
            tickUpper,
            tick,
            self.linearFeeGrowthGlobal0X128 if token == self.token0 else self.linearFeeGrowthGlobal1X128,
        )

        Position.updateLinear(
            position, liquidityDelta, feeGrowthInsideX128
        )

        ## clear any tick data that is no longer needed
        if liquidityDelta < 0:
            if flippedLower:
                Tick.clear(ticksLinearMap, tickLower)
            if flippedUpper:
                Tick.clear(ticksLinearMap, tickUpper)
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

        cacheLinear = SwapCache(feeProtocol, self.liquidityLinear)
        stateLinear = SwapState(
            amountSpecified,
            0,
            slot0Start.sqrtPriceX96,
            slot0Start.tick,
            self.linearFeeGrowthGlobal0X128 if zeroForOne else self.linearFeeGrowthGlobal1X128,
            0,
            cache.liquidityStart,
        )


        if zeroForOne:
            ticksLinearMap = self.ticksLinearTokens1
        else:
            ticksLinearMap = self.ticksLinearTokens0


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
            (step.tickNext, step.initialized) = UniswapPool.nextTick(ticksLinearMap, stateLinear.tick, zeroForOne)
            
            # Temporarily adding this fore debug purposes
            if step.initialized == False:
                # We are in the TICK MIN or TICK MAX, so we can't execute any limit orders
                step = StepComputations(0, 0, 0, 0, 0, 0, 0)
                step.sqrtPriceStartX96 = stateLinear.sqrtPriceX96
            
            else:
                # Do we use the same math as in the linear pool? (aka range orders?)
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
                    stateLinear.sqrtPriceX96,
                    step.amountIn,
                    step.amountOut,
                    step.feeAmount,
                ) = SwapMath.computeSwapStep(
                    stateLinear.sqrtPriceX96,
                    sqrtRatioTargetX96,
                    stateLinear.liquidity,
                    stateLinear.amountSpecifiedRemaining,
                    self.fee,
                )

                if exactInput:
                    stateLinear.amountSpecifiedRemaining -= step.amountIn + step.feeAmount
                    stateLinear.amountCalculated = SafeMath.subInts(
                        stateLinear.amountCalculated, step.amountOut
                    )
                else:
                    stateLinear.amountSpecifiedRemaining += step.amountOut
                    stateLinear.amountCalculated = SafeMath.addInts(
                        stateLinear.amountCalculated, step.amountIn + step.feeAmount
                    )


                ## if the protocol fee is on, calculate how much is owed, decrement feeAmount, and increment protocolFee
                if cache.feeProtocol > 0:
                    delta = abs(step.feeAmount // cache.feeProtocol)
                    step.feeAmount -= delta
                    stateLinear.protocolFee += delta & (2**128 - 1)


                ## shift tick if we reached the next price
                if stateLinear.sqrtPriceX96 == step.sqrtPriceNextX96:
                    ## if the tick is initialized, run the tick transition
                    ## @dev: here is where we should handle the case of an uninitialized boundary tick
                    if step.initialized:
                        liquidity = Tick.crosslinear(
                            ticksLinearMap,
                            step.tickNext,
                            stateLinear.feeGrowthGlobalX128
                            if zeroForOne
                            else self.feeGrowthGlobal0X128
                        )
                        # Should set it to zero
                        stateLinear.liquidity = liquidity
                        assert stateLinear.liquidity == 0
                        # TODO: Remove all the positions included in this tick. But we can't easily get them
                        # since they keys are hashes. This might be the reason
                        # for Uniswapv3 having range orders that can be crossed back again.
                        # Store a dictionary with the positions (keys of self.positionsLinear) for each tick? 
                        # We can only disable/clear the tick if we have first burnt all the positions
                        

                # We CANNOT update tick here because it can be that there is a range order too. Only update ticks if we reach
                # the range orders and we then need to switch.

                #     # Do we need to update the tick here?
                #     state.tick = (step.tickNext - 1) if zeroForOne else step.tickNext
                # elif state.sqrtPriceX96 != step.sqrtPriceStartX96:
                #     ## recompute unless we're on a lower tick boundary (i.e. already transitioned ticks), and haven't moved
                #     state.tick = TickMath.getTickAtSqrtRatio(state.sqrtPriceX96)
                

                
                # Stop the loop if the swap is completed with limit orders
                if (stateLinear.amountSpecifiedRemaining == 0 or stateLinear.sqrtPriceX96 == sqrtPriceLimitX96):
                    # "state" will have the state before Linear orders are executed. Only Amount specified needs to remain
                    state.amountSpecifiedRemaining = stateLinear.amountSpecifiedRemaining                    
                    break




            ######################################################
            #################### RANGE ORDERS ####################
            ######################################################

            # "state" will have the state before Linear orders are executed. Only Amount specified needs to remain
            state.amountSpecifiedRemaining = stateLinear.amountSpecifiedRemaining  


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
        
        if cacheLinear.liquidityStart != stateLinear.liquidity:
            self.liquidityLinear = stateLinear.liquidity

        ## update fee growth global and, if necessary, protocol fees
        ## overflow is acceptable, protocol has to withdraw before it hits type(uint128).max fees

        if zeroForOne:
            self.feeGrowthGlobal0X128 = state.feeGrowthGlobalX128
            self.linearFeeGrowthGlobal0X128 = stateLinear.feeGrowthGlobalX128
            if state.protocolFee > 0:
                self.protocolFees.token0 += state.protocolFee
            if stateLinear.protocolFee > 0:
                self.protocolFees.token0 += stateLinear.protocolFee                
        else:
            self.feeGrowthGlobal1X128 = state.feeGrowthGlobalX128
            self.linearFeeGrowthGlobal1X128 = stateLinear.feeGrowthGlobalX128
            if state.protocolFee > 0:
                self.protocolFees.token1 += state.protocolFee
            if stateLinear.protocolFee > 0:
                self.protocolFees.token1 += stateLinear.protocolFee

        # Add amount calculated in linear orders
        state.amountCalculated += stateLinear.amountCalculated

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

    # TODO: Add collect and burn for linear positions. For positions that have been already used,
    # they will already be burned (somehow, not clear yet). So we can only burn unused positions.
