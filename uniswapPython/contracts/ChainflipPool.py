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
        else:
            ticksLinearMap = self.ticksLinearTokens0

        exactInput = amountSpecified > 0

        state = SwapState(
            amountSpecified,
            0,
            slot0Start.sqrtPriceX96,
            slot0Start.tick,
            self.feeGrowthGlobal0X128 if zeroForOne else self.feeGrowthGlobal1X128,
            0,
            cache.liquidityStart,
            0,
        )

        loopCounter = 0

        while (
            state.amountSpecifiedRemaining != 0
            and state.sqrtPriceX96 != sqrtPriceLimitX96
        ):
            print("SWAP LOOP")
            # We give priority to limit orders being executed first if they offer a better price for the user.

            ######################################################
            #################### LIMIT ORDERS ####################
            ######################################################

            # Probably we can do a simplified version of StepComputations
            stepLinear = StepComputations(0, 0, 0, 0, 0, 0, 0)
            stepLinear.sqrtPriceStartX96 = state.sqrtPriceX96

            # I think we can reuse the nextTick funcion but swapping the zeroForOne input. We want he exact opposite
            # and seems like when zeroForOne we want tick > current one, and when not zeroFor one we want tick <= current one.
            (stepLinear.tickNext, stepLinear.initialized) = nextTickLimitOrder(
                ticksLinearMap, state.tick, not zeroForOne
            )

            if stepLinear.initialized:
                print("Swapping limit orders")

                # Health check (just in case)
                tickLinearInfo = ticksLinearMap[stepLinear.tickNext]
                assert tickLinearInfo.liquidityLeft > 0

                # TODO: Implement this function (math) also updating the tick values (handling crossed and not crossed)
                # Update the fees in the tick here?? We don't keep track of global fees and we cannot update tick fees
                # only when crossed, so we probably need to do it inside this function

                # Get price at that tick
                priceX96 = TickMath.getPriceAtTick(stepLinear.tickNext)
                (
                    stepLinear.amountIn,
                    stepLinear.amountOut,
                    stepLinear.feeAmount,
                    tickCrossed,
                ) = SwapMath.computeLinearSwapStep(
                    priceX96,
                    tickLinearInfo.liquidityLeft,
                    state.amountSpecifiedRemaining,
                    self.fee,
                    zeroForOne,
                )

                # Update the tick
                tickLinearInfo.liquidityLeft = LiquidityMath.addDelta(
                    tickLinearInfo.liquidityLeft, stepLinear.amountOut
                )
                tickLinearInfo.liquiditySwapped = LiquidityMath.addDelta(
                    tickLinearInfo.liquiditySwapped, stepLinear.amountOut
                )

                if tickCrossed:
                    # Health check
                    assert stepLinear.amountOut == tickLinearInfo.liquidityLeft
                    assert tickLinearInfo.liquidityLeft == 0
                    # TODO: Remove all positions in that tick?
                    # I'm not even sure it's necessary in this setup, since they won't be swapped again
                    # We can maybe wait for users to remove them

                if exactInput:
                    state.amountSpecifiedRemaining -= (
                        stepLinear.amountIn + stepLinear.feeAmount
                    )
                    state.amountCalculated = SafeMath.subInts(
                        state.amountCalculated, stepLinear.amountOut
                    )
                else:
                    state.amountSpecifiedRemaining += stepLinear.amountOut
                    state.amountCalculated = SafeMath.addInts(
                        state.amountCalculated,
                        stepLinear.amountIn + stepLinear.feeAmount,
                    )

                # if the protocol fee is on, calculate how much is owed, decrement feeAmount, and increment protocolFee
                if cache.feeProtocol > 0:
                    delta = abs(stepLinear.feeAmount // cache.feeProtocol)
                    stepLinear.feeAmount -= delta
                    state.protocolFee += delta & (2**128 - 1)

                # Calculate linear fees should probably be done also inside the Tick.computeLinearSwapStep function since it
                # will be stored within a tick (most likely)

                # ## update global fee tracker. No need to check for liquidity, otherwise we would not have swapped a LO
                # #if stateLinear.liquidity > 0:
                # state.linearFees += mulDiv(
                #     stepLinear.feeAmount, FixedPoint128_Q128, tickLiquidity
                # )
                # # Addition can overflow in Solidity - mimic it
                # state.linearFees = toUint256(state.linearFees)

                if not tickCrossed:
                    # Health check - swap should be completed
                    assert state.amountSpecifiedRemaining == 0
                    # Prevent from altering anythign in the range order pool
                    break

            print("Starting with Range Orders")

            ######################################################
            #################### RANGE ORDERS ####################
            ######################################################

            step = StepComputations(0, 0, 0, 0, 0, 0, 0)
            step.sqrtPriceStartX96 = state.sqrtPriceX96

            # TODO: Will we need to check the returned initialized state in case we are in the TICK MIN or TICK MAX?
            (step.tickNext, step.initialized) = UniswapPool.nextTick(
                state.tick, zeroForOne
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


def nextTickLimitOrder(tickMapping, tick, lte):
    checkInputTypes(int24=(tick), bool=(lte))

    print("tick:", tick)
    print("lte:", lte)
    print("tickMapping:", tickMapping)

    if not tickMapping.__contains__(tick):
        # If tick doesn't exist in the mapping we fake it (easier than searching for nearest value)
        sortedKeyList = sorted(list(tickMapping.keys()) + [tick])
    else:
        sortedKeyList = sorted(list(tickMapping.keys()))

    indexCurrentTick = sortedKeyList.index(tick)

    if lte:
        # If the current tick is initialized (not faked), we return the current tick
        if tickMapping.__contains__(tick):
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
