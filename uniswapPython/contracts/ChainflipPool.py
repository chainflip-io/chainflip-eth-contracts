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

        (
            position,
            liquidityLeftDelta,
            liquiditySwappedDelta,
        ) = self._modifyPositionLinearOrder(
            token, ModifyLinearPositionParams(recipient, tick, amount)
        )
        # Health check (these values are not very relevant in minting)
        assert liquidityLeftDelta == amount
        assert liquiditySwappedDelta == 0

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

        (
            position,
            liquidityLeftDelta,
            liquiditySwappedDelta,
        ) = self._updatePositionLinearOrder(
            token,
            params.owner,
            params.tick,
            params.liquidityDelta,
        )

        return position, liquidityLeftDelta, liquiditySwappedDelta

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
        if token == self.token0:
            ticksLinearMap = self.ticksLinearTokens0
        else:
            ticksLinearMap = self.ticksLinearTokens1

        # Update Position before updating the tick because we need to calculate how the liquidityDelta
        # translates to difference of liquidity (liquidityLeftDelta) when burning
        liquidityLeftDelta, liquiditySwappedDelta = Position.updateLinear(
            position,
            liquidityDelta,
            # If we mint for the first time and the corresponding tick doesn't exist, we initialize with 0
            ticksLinearMap[tick].amountSwappedInsideX128
            if ticksLinearMap.__contains__(tick)
            else 0,
            token == self.token0,
            TickMath.getPriceAtTick(tick),
            # If we mint for the first time and the corresponding tick doesn't exist, we initialize with 0
            ticksLinearMap[tick].feeGrowthInsideX128
            if ticksLinearMap.__contains__(tick)
            else 0,
        )

        # Initialize values
        flipped = False

        ## if we need to update the ticks, do it.
        if liquidityDelta != 0:
            (flipped) = Tick.updateLinear(
                ticksLinearMap,
                tick,
                liquidityLeftDelta,
                liquidityDelta,
                # liquidityDelta,
                # self.linearFeeGrowthGlobal1X128
                # if token == self.token0
                # else self.linearFeeGrowthGlobal0X128,
                self.maxLiquidityPerTick,
                # token == self.token0,
            )

        if flipped:
            assert tick % self.tickSpacing == 0  ## ensure that the tick is spaced

        ## clear any tick data that is no longer needed
        if liquidityDelta < 0:
            if flipped:
                Tick.clear(ticksLinearMap, tick)
        return position, liquidityLeftDelta, liquiditySwappedDelta

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
            liquidityLeftDelta,
            liquiditySwappedDelta,
        ) = self._modifyPositionLinearOrder(
            token,
            ModifyLinearPositionParams(recipient, tick, -amount),
        )

        # Health check
        if amount == 0:
            assert liquidityLeftDelta == 0
            assert liquiditySwappedDelta == 0

        # Return amounts in the right order token0#token1
        (amountBurnt0, amountBurnt1) = (
            (abs(liquidityLeftDelta), abs(liquiditySwappedDelta))
            if token == self.token0
            else (abs(liquiditySwappedDelta), abs(liquidityLeftDelta))
        )

        # As in uniswap we return the amount of tokens that were burned, that is without fees accrued.
        return (
            recipient,
            tick,
            amount,
            amountBurnt0,
            amountBurnt1,
        )

    ### @inheritdoc IUniswapV3PoolActions
    def collectLinear(
        self,
        recipient,
        token,
        tick,
        amount0Requested,
        amount1Requested,
    ):
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

        amountPos0 = (
            position.tokensOwed0
            if (amount0Requested > position.tokensOwed0)
            else amount0Requested
        )
        amountPos1 = (
            position.tokensOwed1
            if (amount1Requested > position.tokensOwed1)
            else amount1Requested
        )

        if amountPos0 > 0:
            position.tokensOwed0 -= amountPos0
            self.transferToken(recipient, self.token0, amountPos0)
        if amountPos1 > 0:
            position.tokensOwed1 -= amountPos1
            self.transferToken(recipient, self.token1, amountPos1)

        # For debugging doing it like this, but we probably need to return both (or merge them)
        # return (recipient, tick, amount0, amount1, amountPos0, amountPos1)
        return (recipient, tick, amountPos0, amountPos1)

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
            # Return a list of sorted keys with liquidityLeft > 0
            getKeysLinearTicksWithLiquidity(ticksLinearMap),
        )

        while (
            state.amountSpecifiedRemaining != 0
            and state.sqrtPriceX96 != sqrtPriceLimitX96
        ):
            print("SWAP LOOP")
            # First limit orders are checked since they can offer a better price for the user.

            ######################################################
            #################### LIMIT ORDERS ####################
            ######################################################

            # Probably we can do a simplified version of StepComputations
            stepLinear = StepComputations(0, 0, False, 0, None, 0, 0)
            stepLinear.sqrtPriceStartX96 = state.sqrtPriceX96

            # Just to not try finding a limit order if there aren't any
            if len(state.keysLinearTicks) != 0:
                # Find the next linear order tick. initialized == False if not found and returning the next best
                (stepLinear.tickNext, stepLinear.initialized) = nextLinearTick(
                    state.keysLinearTicks, not zeroForOne, state.tick
                )

                print("Next tick: ", stepLinear.tickNext)

                # If !initialized then there are no more linear ticks with liquidityLeft > 0 that we can swap for now
                if stepLinear.initialized:
                    tickLinearInfo = ticksLinearMap[stepLinear.tickNext]

                    # Health check
                    assert tickLinearInfo.liquidityLeft > 0

                    print("Swapping limit orders")

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

                    # Update the tick - we can consider to only update when we cross tick
                    # and keep global variables in state (like uniswap does)

                    # Update the tick amountSwappedInsideLastX128 - For now we dont handle overflow (?)
                    # Using liquidityLeft before it has been updated
                    tickLinearInfo.amountSwappedInsideX128 += mulDiv(
                        stepLinear.amountOut,
                        FixedPoint128_Q128,
                        tickLinearInfo.liquidityLeft,
                    )

                    # Update tick liquidity
                    ## Health check
                    assert stepLinear.amountOut > 0
                    tickLinearInfo.liquidityLeft = LiquidityMath.addDelta(
                        tickLinearInfo.liquidityLeft, -stepLinear.amountOut
                    )

                    if tickCrossed:
                        # Health check
                        assert tickLinearInfo.liquidityLeft == 0
                        # TODO: Remove all positions in that tick?
                        # I'm not even sure it's necessary in this setup. They won't be swapped again
                        # since we handle crossed ticks. And they are not range orders so they won't
                        # be crossed in the opposite direction. We can maybe wait for users to remove them.

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

                    # Calculate linear fees can probably be done inside the Tick.computeLinearSwapStep function since it
                    # will be stored within a tick (most likely). For now we keep it here to have the same structure.

                    ## update global fee tracker. No need to check for liquidity, otherwise we would not have swapped a LO
                    # if stateLinear.liquidity > 0:
                    # feeAmount is in amountIn tokens => therefore feeGrowthInsideX128 is not in liquidityTokens
                    tickLinearInfo.feeGrowthInsideX128 += mulDiv(
                        stepLinear.feeAmount,
                        FixedPoint128_Q128,
                        tickLinearInfo.liquidityGross,
                    )
                    # Addition can overflow in Solidity - mimic it
                    tickLinearInfo.feeGrowthInsideX128 = toUint256(
                        tickLinearInfo.feeGrowthInsideX128
                    )

                    if not tickCrossed:
                        # Health check - swap should be completed
                        assert state.amountSpecifiedRemaining == 0
                        # Prevent from altering anythign in the range order pool
                        break
                    else:
                        # There might be another Limit order that is better than range orders
                        continue

            print("Starting with Range Orders")

            # For development purposes only
            # assert False, "We should not go into range orders"

            ######################################################
            #################### RANGE ORDERS ####################
            ######################################################

            step = StepComputations(0, 0, 0, 0, 0, 0, 0)
            step.sqrtPriceStartX96 = state.sqrtPriceX96

            # TODO: Will we need to check the returned initialized state in case we are in the TICK MIN or TICK MAX?
            (step.tickNext, step.initialized) = self.nextTick(state.tick, zeroForOne)

            ## get the price for the next tick
            step.sqrtPriceNextX96 = TickMath.getSqrtRatioAtTick(step.tickNext)

            if not step.initialized:
                # We know it's a border and we have no liquidity, so we rather just zero-swap until there
                assert self.liquidity == 0
                # if we have the next best LO
                print("stepLinear", stepLinear)
                if not stepLinear.initialized and stepLinear.tickNext != None:
                    if zeroForOne:
                        sqrtRatioTargetX96 = TickMath.getSqrtRatioAtTick(
                            stepLinear.tickNext - 1
                        )
                    else:
                        sqrtRatioTargetX96 = TickMath.getSqrtRatioAtTick(
                            stepLinear.tickNext - 1
                        )
            else:
                # We could set the TickMath.getSqrtRatioAtTick(stepLinear.tickNext) also as a limit price, so if we reach
                # there by swapping a RO, we stop, jump to the LO, and then come back to the RO if needed. Otherwise, we
                # can just leave it like this, so it will swap until the limit/next price. Then on a future swap, that LO
                # will be able to be used. TODO: Explore this.

                ## compute values to swap to the target tick, price limit, or point where input#output amount is exhausted.
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

            # Continue the range order swap as normal
            state.sqrtPriceX96 = state.sqrtPriceX96

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


# Remove all ticks with LiquidityLeft == 0. Maybe we end up not needing that if we automatically remove the positions
# after swap, but probably we won't
def getKeysLinearTicksWithLiquidity(tickMapping):
    # Dictionary with ticks that have liquidityLeft > 0
    dictTicksWithLiq = {
        k: v for k, v in tickMapping.items() if tickMapping[k].liquidityLeft > 0
    }

    # Return a list of sorted keys
    return sorted(list(dictTicksWithLiq.keys()))


# Find the next linearTick (all should have liquidityLeft > 0) and pop them from the list. The input list
# should be a list of sorted keys.
def nextLinearTick(keysLinearTicks, lte, currentTick):
    checkInputTypes(bool=(lte))

    # Only pop the value if tick will be used
    if lte:
        # Start from the most left
        if keysLinearTicks[0] <= currentTick:
            nextTick = keysLinearTicks.pop(0)
            return nextTick, True
        nextTick = keysLinearTicks[0]
    else:
        if keysLinearTicks[-1] > currentTick:
            # Start from the most right
            nextTick = keysLinearTicks.pop(-1)
            return nextTick, True
        nextTick = keysLinearTicks[-1]

    # If no tick with LO is found, then we're done - not modifying the keyList in case we can use
    # any of the ticks later in the swap, since current tick on the rangeOrder pool can change.
    # However, we return the next best tick so the range orders know (without popping)
    return nextTick, False
