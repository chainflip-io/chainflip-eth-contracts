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

        self.liquidityLinear0 = 0
        self.liquidityLinear1 = 0

        # Creating two different dicts, one for each type of limit orders (token0 and token1)
        self.ticksLinearTokens0 = dict()
        self.ticksLinearTokens1 = dict()

        self.linearFeeGrowthGlobal0X128 = 0
        self.linearFeeGrowthGlobal1X128 = 0

        # Pass all paramaters to UniswapPool's constructor
        super().__init__(token0, token1, fee, tickSpacing)

    def mintLinearOrder(self, token, recipient, tickLower, tickUpper, amount):
        checkInputTypes(
            string=token,
            accounts=(recipient),
            int24=(tickLower, tickUpper),
            uint128=(amount),
        )
        assert amount > 0
        assert (
            token == self.token0 or token == self.token1
        ), "Token not part of the pool"

        (_, amountIn) = self._modifyPositionLinearOrder(
            token, ModifyPositionParams(recipient, tickLower, tickUpper, amount)
        )

        amountIn = toUint256(abs(amountIn))

        if token == self.token0:
            recipient.transferToken(self, self.token0, amountIn)
        elif token == self.token1:
            recipient.transferToken(self, self.token1, amountIn)

        return amountIn

    def _modifyPositionLinearOrder(self, token, params):
        checkInputTypes(
            string=token,
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

            if not (
                self.slot0.tick >= params.tickUpper
                and self.slot0.tick < params.tickUpper
            ):
                if token == self.token0:
                    self.liquidityLinear0 = LiquidityMath.addDelta(
                        self.liquidityLinear0, params.liquidityDelta
                    )
                else:
                    self.liquidityLinear1 = LiquidityMath.addDelta(
                        self.liquidityLinear1, params.liquidityDelta
                    )

        return (position, amount)

    def _updatePositionLinearOrder(
        self, token, owner, tickLower, tickUpper, liquidityDelta, tick
    ):
        checkInputTypes(
            string=token,
            accounts=(owner),
            int24=(tickLower, tickUpper, tick),
            int128=(liquidityDelta),
        )
        # This will create a position if it doesn't exist
        position = Position.getLinear(
            self.linearPositions, owner, tickLower, tickUpper, token == self.token0
        )

        # Initialize values
        flippedLower = flippedUpper = False
        ## if we need to update the ticks, do it
        if liquidityDelta != 0:
            if token == self.token0:
                ticksLinearMap = self.ticksLinearTokens0
            else:
                ticksLinearMap = self.ticksLinearTokens1
            flippedLower = Tick.updateLinear(
                ticksLinearMap,
                tickLower,
                tick,
                liquidityDelta,
                self.linearFeeGrowthGlobal1X128
                if token == self.token0
                else self.linearFeeGrowthGlobal0X128,
                False,
                self.maxLiquidityPerTick,
                token == self.token0,
            )
            flippedUpper = Tick.updateLinear(
                ticksLinearMap,
                tickUpper,
                tick,
                liquidityDelta,
                self.linearFeeGrowthGlobal1X128
                if token == self.token0
                else self.linearFeeGrowthGlobal0X128,
                True,
                self.maxLiquidityPerTick,
                token == self.token0,
            )

        if flippedLower:
            assert tickLower % self.tickSpacing == 0  ## ensure that the tick is spaced
        if flippedUpper:
            assert tickUpper % self.tickSpacing == 0  ## ensure that the tick is spaced

        # If position is token0, the fees will be in token1
        feeGrowthInsideX128 = Tick.getFeeGrowthInsideLinear(
            ticksLinearMap,
            tickLower,
            tickUpper,
            tick,
            self.linearFeeGrowthGlobal1X128
            if token == self.token0
            else self.linearFeeGrowthGlobal0X128,
        )
        Position.updateLinear(position, liquidityDelta, feeGrowthInsideX128)

        ## clear any tick data that is no longer needed
        if liquidityDelta < 0:
            if flippedLower:
                Tick.clear(ticksLinearMap, tickLower)
            if flippedUpper:
                Tick.clear(ticksLinearMap, tickUpper)
        return position

    # This can only be run if the order has only been partially crossed. If fully crossed, the positions
    # will have been burnt automatically.
    def burnLimitOrder(self, token, recipient, tickLower, tickUpper, amount):
        checkInputTypes(
            string=token,
            accounts=(recipient),
            int24=(tickLower, tickUpper),
            uint128=(amount),
        )

        # Add check if the position exists - when poking an uninitialized position it can be that
        # getFeeGrowthInside finds a non-initialized tick before Position.update reverts.
        Position.assertLimitPositionExists(
            self.linearPositions, recipient, tickLower, tickUpper, token == self.token0
        )

        # Added extra recipient input variable to mimic msg.sender
        (position, amountInt) = self._modifyPositionLinearOrder(
            token,
            ModifyPositionParams(recipient, tickLower, tickUpper, -amount),
        )

        # Mimic conversion to uint256
        amount = abs(-amountInt) & (2**256 - 1)

        if amount > 0:
            position.tokensOwed += amount

        return (recipient, tickLower, tickUpper, amount, amount)

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

        if zeroForOne:
            ticksLinearMap = self.ticksLinearTokens1
            cacheLinear = SwapCache(feeProtocol, self.liquidityLinear1)
        else:
            ticksLinearMap = self.ticksLinearTokens0
            cacheLinear = SwapCache(feeProtocol, self.liquidityLinear0)

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

        stateLinear = SwapState(
            amountSpecified,
            0,
            slot0Start.sqrtPriceX96,
            slot0Start.tick,
            self.linearFeeGrowthGlobal0X128
            if zeroForOne
            else self.linearFeeGrowthGlobal1X128,
            0,
            cacheLinear.liquidityStart,
        )

        amountSpecifiedRemaining = amountSpecified
        sqrtPriceX96 = state.sqrtPriceX96
        assert state.sqrtPriceX96 == stateLinear.sqrtPriceX96

        loopCounter = 0

        while (
            amountSpecifiedRemaining != 0
            and sqrtPriceX96 != sqrtPriceLimitX96
        ):
            print("SWAP LOOP")
            # For now we give priority to limit orders being executed first. In the future we might want to compare
            # and execute the one that gives a higher price. That makes things too complicated for now.

            ##TODO: Add someting like doing both swaps (or comparing current ticks for Linear & range) and choose one.
            # Then skip the other one because the best option might be to do two swaps of the same kind.

            ######################################################
            #################### LIMIT ORDERS ####################
            ######################################################

            stepLinear = StepComputations(0, 0, 0, 0, 0, 0, 0)
            stepLinear.sqrtPriceStartX96 = stateLinear.sqrtPriceX96

            # TODO: Will we need to check the returned initialized state in case we are in the TICK MIN or TICK MAX?
            (stepLinear.tickNext, stepLinear.initialized) = UniswapPool.nextTick(
                ticksLinearMap, stateLinear.tick, zeroForOne
            )
            print("Tick before linear order: ", stateLinear.tick)
            print("Next tick linear order: ", stepLinear.tickNext)

            stepLinear.sqrtPriceNextX96 = TickMath.getSqrtRatioAtTick(stepLinear.tickNext)

            ## compute values to swap to the target tick, price limit, or point where input#output amount is exhausted
            if zeroForOne:
                sqrtRatioTargetX96 = (
                    sqrtPriceLimitX96
                    if stepLinear.sqrtPriceNextX96 < sqrtPriceLimitX96
                    else stepLinear.sqrtPriceNextX96
                )
            else:
                sqrtRatioTargetX96 = (
                    sqrtPriceLimitX96
                    if stepLinear.sqrtPriceNextX96 > sqrtPriceLimitX96
                    else stepLinear.sqrtPriceNextX96
                )

            (
                stateLinear.sqrtPriceX96,
                stepLinear.amountIn,
                stepLinear.amountOut,
                stepLinear.feeAmount,
            ) = SwapMath.computeSwapStep(
                stateLinear.sqrtPriceX96,
                sqrtRatioTargetX96,
                stateLinear.liquidity,
                amountSpecifiedRemaining,
                self.fee,
            )

            if exactInput:
                amountSpecifiedRemaining -= stepLinear.amountIn + stepLinear.feeAmount
                stateLinear.amountCalculated = SafeMath.subInts(
                    stateLinear.amountCalculated, stepLinear.amountOut
                )
            else:
                amountSpecifiedRemaining += stepLinear.amountOut
                stateLinear.amountCalculated = SafeMath.addInts(
                    stateLinear.amountCalculated, stepLinear.amountIn + stepLinear.feeAmount
                )

            ## if the protocol fee is on, calculate how much is owed, decrement feeAmount, and increment protocolFee
            if cache.feeProtocol > 0:
                delta = abs(stepLinear.feeAmount // cache.feeProtocol)
                stepLinear.feeAmount -= delta
                stateLinear.protocolFee += delta & (2**128 - 1)

            ## update global fee tracker
            if stateLinear.liquidity > 0:
                stateLinear.feeGrowthGlobalX128 += mulDiv(
                    stepLinear.feeAmount, FixedPoint128_Q128, stateLinear.liquidity
                )
                # Addition can overflow in Solidity - mimic it
                stateLinear.feeGrowthGlobalX128 = toUint256(stateLinear.feeGrowthGlobalX128)

            ## shift tick if we reached the next price
            if stateLinear.sqrtPriceX96 == stepLinear.sqrtPriceNextX96:
                ## if the tick is initialized, run the tick transition
                ## @dev: here is where we should handle the case of an uninitialized boundary tick
                if stepLinear.initialized:
                    print("CROSSING TICK")
                    liquidityNet = Tick.crosslinear(
                        ticksLinearMap,
                        stepLinear.tickNext,
                        stateLinear.feeGrowthGlobalX128
                        if zeroForOne
                        else self.linearFeeGrowthGlobal0X128,
                    )
                    #TODO: Check if this makes sense and if it's working
                    # For now only remove some liquidity
                    if zeroForOne:
                        liquidityNet = - liquidityNet
                    stateLinear.liquidity = LiquidityMath.addDelta(
                        stateLinear.liquidity, liquidityNet
                    )
                    # TODO: Should set the tick Liquidity to zero (old tick) and remove all 
                    # the positions included in this tick. But we can't easily get them
                    # since they keys are hashes. This might be the reason
                    # for Uniswapv3 having range orders that can be crossed back again.
                    # Store a dictionary with the positions (keys of self.positionsLinear) for each tick?
                    # We can only disable/clear the tick if we have first burnt all the positions

            # We CANNOT update tick here because it can be that there is a range order too. Only update ticks if we reach
            # the range orders and we then need to switch.

                # Do we need to update the tick here?
                stateLinear.tick = (stepLinear.tickNext - 1) if zeroForOne else stepLinear.tickNext
            elif stateLinear.sqrtPriceX96 != stepLinear.sqrtPriceStartX96:
                ## recompute unless we're on a lower tick boundary (i.e. already transitioned ticks), and haven't moved
                stateLinear.tick = TickMath.getTickAtSqrtRatio(stateLinear.sqrtPriceX96)

            print("OUTPUT OF LINEAR TICK calculations: ", stateLinear.tick)
            # Stop the loop if the swap is completed with limit orders
            if (
                amountSpecifiedRemaining != 0
                and stateLinear.sqrtPriceX96 != sqrtPriceLimitX96
            ):

                # For debugging purposes - we should not be using range orders
                #assert False
                print("Starting with Range Orders")

                ######################################################
                #################### RANGE ORDERS ####################
                ######################################################

                step = StepComputations(0, 0, 0, 0, 0, 0, 0)
                step.sqrtPriceStartX96 = state.sqrtPriceX96

                # TODO: Will we need to check the returned initialized state in case we are in the TICK MIN or TICK MAX?
                (step.tickNext, step.initialized) = UniswapPool.nextTick(
                    self.ticks, state.tick, zeroForOne
                )

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
                    amountSpecifiedRemaining,
                    self.fee,
                )

                if exactInput:
                    amountSpecifiedRemaining -= step.amountIn + step.feeAmount
                    state.amountCalculated = SafeMath.subInts(
                        state.amountCalculated, step.amountOut
                    )
                else:
                    amountSpecifiedRemaining += step.amountOut
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

        
            ## Leave the state.tick and price separate for the Range and Limit order swaps. We will most likely need to
            ## compare them at the begining of the loop.


            # Temporal to prevent infinite loop
            loopCounter += 1
            if loopCounter == 5:
                assert False

        ## End of swap loop
        # Set final tick as the range tick
        if state.tick != slot0Start.tick:
            self.slot0.sqrtPriceX96 = state.sqrtPriceX96
            self.slot0.tick = state.tick
        else:
            ## otherwise just update the price
            self.slot0.sqrtPriceX96 = state.sqrtPriceX96


        # FOR DEBUGGING PURPOSES - to check buurned half-swapped positions
        self.slot0.sqrtPriceX96 = stateLinear.sqrtPriceX96
        self.slot0.tick = stateLinear.tick

        # if state.tick != slot0Start.tick:
        #     if zeroForOne:
        #         self.slot0.sqrtPriceX96 = max(
        #             state.sqrtPriceX96, stateLinear.sqrtPriceX96
        #         )
        #         self.slot0.tick = max(state.tick, stateLinear.tick)
        #     else:
        #         self.slot0.sqrtPriceX96 = min(
        #             state.sqrtPriceX96, stateLinear.sqrtPriceX96
        #         )
        #         self.slot0.tick = min(state.tick, stateLinear.tick)
        # else:
        #     ## otherwise just update the price
        #     if zeroForOne:
        #         self.slot0.sqrtPriceX96 = max(
        #             state.sqrtPriceX96, stateLinear.sqrtPriceX96
        #         )
        #     else:
        #         self.slot0.sqrtPriceX96 = min(
        #             state.sqrtPriceX96, stateLinear.sqrtPriceX96
        #         )

        ## update liquidity if it changed
        if cache.liquidityStart != state.liquidity:
            self.liquidity = state.liquidity

        if cacheLinear.liquidityStart != stateLinear.liquidity:
            if zeroForOne:
                self.liquidityLinear1 = stateLinear.liquidity
            else:
                self.liquidityLinear0 = stateLinear.liquidity

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
            (amountSpecified - amountSpecifiedRemaining, state.amountCalculated)
            if (zeroForOne == exactInput)
            else (
                state.amountCalculated,
                amountSpecified - amountSpecifiedRemaining,
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
