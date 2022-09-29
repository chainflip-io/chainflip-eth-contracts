import sys, os

import Tick
import TickMath
import SwapMath
import LiquidityMath
import Position
import LimitOrderMath
import SafeMath
from UniswapPool import *

sys.path.append(os.path.join(os.path.dirname(sys.path[0]), "tests"))
from utilities import *

from dataclasses import dataclass


@dataclass
class ModifyLimitPositionParams:
    ## the address that owns the position
    owner: int
    ## the tick of the position
    tick: int
    ## any change in liquidity
    liquidityDelta: int


class ChainflipPool(UniswapPool):
    def __init__(self, token0, token1, fee, tickSpacing, ledger):
        checkInputTypes(string=(token0, token1), uint24=(fee), int24=(tickSpacing))

        # Setting default to rounding down as default since the majority of the math requires rounding down
        LimitOrderMath.setDecimalPrecRound(contextPrecision, "ROUND_DOWN")

        # For now both token0 and token1 limit orders on the same mapping. Maybe we will need to keep them
        # somehow else to be able to remove them after a tick is crossed.
        self.limitOrders = dict()

        # Creating two different dicts, one for each type of limit orders (token0 and token1)
        self.ticksLimitTokens0 = dict()
        self.ticksLimitTokens1 = dict()

        # Pass all paramaters to UniswapPool's constructor
        super().__init__(token0, token1, fee, tickSpacing, ledger)

    ### @dev Common checks for valid tick inputs.
    def checkTick(tick):
        checkInputTypes(int24=(tick))
        # Check that priceTick > 0 to simplify edge cases (this happens because pricex96 can be zero
        # in some ticks while sqrtPricex96 will not).
        assert tick >= TickMath.MIN_TICK_LO, "TLM"
        assert tick <= TickMath.MAX_TICK_LO, "TUM"

    def mintLimitOrder(self, token, recipient, tick, amount):
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
        ) = self._modifyPositionLimitOrder(
            token, ModifyLimitPositionParams(recipient, tick, amount)
        )
        # Health check (these values are not very relevant in minting)
        assert liquidityLeftDelta == amount
        assert liquiditySwappedDelta == 0

        amountIn = toUint256(abs(amount))

        if token == self.token0:
            self.ledger.transferToken(recipient, self, self.token0, amountIn)
        elif token == self.token1:
            self.ledger.transferToken(recipient, self, self.token1, amountIn)

        return amountIn

    def _modifyPositionLimitOrder(self, token, params):
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
        ) = self._updatePositionLimitOrder(
            token,
            params.owner,
            params.tick,
            params.liquidityDelta,
        )

        return position, liquidityLeftDelta, liquiditySwappedDelta

    def _updatePositionLimitOrder(self, token, owner, tick, liquidityDelta):
        checkInputTypes(
            string=token,
            accounts=(owner),
            int24=(tick),
            int128=(liquidityDelta),
        )
        # This will create a position if it doesn't exist
        position, created = Position.getLimit(
            self.limitOrders, owner, tick, token == self.token0
        )
        # We could return a bool to assert if position has just been created
        if created:
            assert liquidityDelta > 0

        if token == self.token0:
            ticksLimitMap = self.ticksLimitTokens0
        else:
            ticksLimitMap = self.ticksLimitTokens1

        # Initialize values
        flipped = False

        ## if we need to update the ticks, do it.
        if liquidityDelta != 0:
            (flipped) = Tick.updateLimit(
                ticksLimitMap,
                tick,
                liquidityDelta,
                self.maxLiquidityPerTick,
                created,
                owner,
            )

        (liquidityLeftDelta, liquiditySwappedDelta,) = Position.updateLimit(
            position,
            liquidityDelta,
            # If we mint for the first time and the corresponding tick doesn't exist, we initialize with 0
            ticksLimitMap[tick].oneMinusPercSwap,
            token == self.token0,
            TickMath.getPriceAtTick(tick),
            # If we mint for the first time and the corresponding tick doesn't exist, we initialize with 0
            ticksLimitMap[tick].feeGrowthInsideX128,
            created,
        )

        if flipped:
            assert tick % self.tickSpacing == 0  ## ensure that the tick is spaced

        ## clear any tick data that is no longer needed
        if liquidityDelta < 0:
            if flipped:
                Tick.clear(ticksLimitMap, tick)
            # If position is burnt but not tick, we need to remove the owner from tick.ownerPositions.
            # Position will be removed later after tokens have been collected.
            elif position.liquidity == 0:
                print("")
                # Tick should contain the owner
                ticksLimitMap[tick].ownerPositions.remove(owner)
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
            self.limitOrders, recipient, tick, token == self.token0
        )

        # Added extra recipient input variable to mimic msg.sender
        (
            position,
            liquidityLeftDelta,
            liquiditySwappedDelta,
        ) = self._modifyPositionLimitOrder(
            token,
            ModifyLimitPositionParams(recipient, tick, -amount),
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

        # If position is fully burnt, automatically collect all the fees. Probably could do a simplified version.
        # At this point the tick might not exist (might have been burnt in the previous step)
        # amountBurnt will be overwritten by collectLimitOrder if tick is fully burnt, and will also include fees
        # NOTE: We might want to return separate values instead of overwriting amountBurnt
        if position.liquidity == 0:
            (recipient, tick, amountBurnt0, amountBurnt1) = self.collectLimitOrder(
                recipient, token, tick, MAX_UINT128, MAX_UINT128
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
    def collectLimitOrder(
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
        # even thought we would remove anyway at the end, but just for clarity.
        key = Position.assertLimitPositionExists(
            self.limitOrders, recipient, tick, token == self.token0
        )

        ## we don't need to checkTicks here, because invalid positions will never have non-zero tokensOwed{0,1}
        ## Hardcoded recipient == msg.sender.
        position, _ = Position.getLimit(
            self.limitOrders, recipient, tick, token == self.token0
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

        assert self.balances[self.token0] >= amountPos0
        assert self.balances[self.token1] >= amountPos1

        if amountPos0 > 0:
            position.tokensOwed0 -= amountPos0
            self.ledger.transferToken(self, recipient, self.token0, amountPos0)
        if amountPos1 > 0:
            position.tokensOwed1 -= amountPos1
            self.ledger.transferToken(self, recipient, self.token1, amountPos1)

        # Clear the position for bookkeeping purposes
        # NOTE: This is no strictly necessary, we could leave the position as UniSwap does. However, Solidity's memory
        # usage/requirements doesn't really depend on clearing positions. In Python (and also Rust I suspect) this matters,
        # so we would rather clear the positions.
        if position.liquidity == 0:
            # We should get the hash when getLimit is calculated before
            del self.limitOrders[key]

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
            ticksLimitMap = self.ticksLimitTokens1
        else:
            ticksLimitMap = self.ticksLimitTokens0

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
            # NOTE: If storing an array with all the tick keys is too computationally expensive we can just
            # get the next tick when running nextLimitTick every time.
            getKeysLimitTicksWithLiquidity(ticksLimitMap),
            [],
        )

        while (
            state.amountSpecifiedRemaining != 0
            and state.sqrtPriceX96 != sqrtPriceLimitX96
        ):
            # First limit orders are checked since they can offer a better price for the user.
            ######################################################
            #################### LIMIT ORDERS ####################
            ######################################################

            # Probably we can do a simplified version of StepComputations
            stepLimit = StepComputations(0, None, False, 0, 0, 0, 0)
            stepLimit.sqrtPriceStartX96 = state.sqrtPriceX96

            # Just to not try finding a limit order if there aren't any.
            if len(state.keysLimitTicks) != 0:
                # Find the next linear order tick. initialized == False if not found and returning the next best
                (stepLimit.tickNext, stepLimit.initialized) = nextLimitTick(
                    state.keysLimitTicks, not zeroForOne, state.tick
                )
                # If !initialized then there are no more linear ticks with liquidityLeft > 0 that we can swap for now
                if stepLimit.initialized:

                    tickLimitInfo = ticksLimitMap[stepLimit.tickNext]

                    # Health check
                    assert tickLimitInfo.oneMinusPercSwap > 0
                    # Get price at that tick
                    priceX96 = TickMath.getPriceAtTick(stepLimit.tickNext)
                    (
                        stepLimit.amountIn,
                        stepLimit.amountOut,
                        stepLimit.feeAmount,
                        tickCrossed,
                        resultingOneMinusPercSwap,
                    ) = SwapMath.computeLimitSwapStep(
                        priceX96,
                        tickLimitInfo.liquidityGross,
                        state.amountSpecifiedRemaining,
                        self.fee,
                        zeroForOne,
                        tickLimitInfo.oneMinusPercSwap,
                    )

                    # Health check
                    assert tickLimitInfo.oneMinusPercSwap <= Decimal("1")

                    # Update oneMinusPercSwap with the value calculated
                    tickLimitInfo.oneMinusPercSwap = resultingOneMinusPercSwap

                    if exactInput:
                        state.amountSpecifiedRemaining -= (
                            stepLimit.amountIn + stepLimit.feeAmount
                        )
                        state.amountCalculated = SafeMath.subInts(
                            state.amountCalculated, stepLimit.amountOut
                        )
                    else:
                        state.amountSpecifiedRemaining += stepLimit.amountOut
                        state.amountCalculated = SafeMath.addInts(
                            state.amountCalculated,
                            stepLimit.amountIn + stepLimit.feeAmount,
                        )

                    # if the protocol fee is on, calculate how much is owed, decrement feeAmount, and increment protocolFee
                    if cache.feeProtocol > 0:
                        delta = abs(stepLimit.feeAmount // cache.feeProtocol)
                        stepLimit.feeAmount -= delta
                        state.protocolFee += delta & (2**128 - 1)

                    # Calculate linear fees can probably be done inside the Tick.computeLimitSwapStep function since it
                    # will be stored within a tick (most likely). For now we keep it here to have the same structure.

                    ## update global fee tracker. No need to check for liquidity, otherwise we would not have swapped a LO
                    # if stateLimit.liquidity > 0:
                    # feeAmount is in amountIn tokens => therefore feeGrowthInsideX128 is not in liquidityTokens
                    tickLimitInfo.feeGrowthInsideX128 += mulDiv(
                        stepLimit.feeAmount,
                        FixedPoint128_Q128,
                        tickLimitInfo.liquidityGross,
                    )
                    # Addition can overflow in Solidity - mimic it
                    tickLimitInfo.feeGrowthInsideX128 = toUint256(
                        tickLimitInfo.feeGrowthInsideX128
                    )

                    if tickCrossed:
                        # Health check
                        assert tickLimitInfo.oneMinusPercSwap == 0
                        # Burn all the positions in that tick and clear the tick itself. This could be also done
                        # in a separate call if desired, but then it needs to be right after the swap.
                        # The last position burnt should already clear the tick, no need to do it here.
                        # Since we don't transfer tokens until the end of the swap, we can't really burn and give tokens here.
                        # We will burn them at the end of the swap
                        state.ticksCrossed.append(stepLimit.tickNext)
                        # There might be another Limit order that is better than range orders
                        if state.amountSpecifiedRemaining != 0:
                            continue
                        else:
                            # In case we cross the tick at the exact some time we complete the order
                            break
                    else:
                        # Health check - swap should be completed
                        assert state.amountSpecifiedRemaining == 0
                        # Prevent from altering anything in the range order pool
                        break

            ######################################################
            #################### RANGE ORDERS ####################
            ######################################################
            step = StepComputations(0, 0, 0, 0, 0, 0, 0)
            step.sqrtPriceStartX96 = state.sqrtPriceX96

            (step.tickNext, step.initialized) = self.nextTick(state.tick, zeroForOne)

            ## get the price for the next tick
            step.sqrtPriceNextX96 = TickMath.getSqrtRatioAtTick(step.tickNext)

            # NOTE: Having this check to understand the behaviour of the Range Order when the pool tends towards the limit with
            # no liquidity. It is also a valid check regardless of whether this is a border or not - the same logic should apply.
            # This check can be removed.
            if not step.initialized:
                # We know it's a border and we have no liquidity, so instead of zero-swapping until there
                # we just stop at the LO tick.
                assert state.liquidity == 0

            # If there is a "next best" LO, use the TickMath.getSqrtRatioAtTick(stepLimit.tickNext) also as a limit price,
            # so if we reach there by swapping a RO, we stop, jump to the LO, and then come back to the RO if needed.
            # This is because we can't know the RO final price, and it could be a lot worse than the LO price. We could also
            # calculate the range order final price, compare it with the LO price, and then decide whether to swap the LO.
            # NOTE: A margin tick(s) could be added here before we jump into LO. Could potentially be used to tweak the
            # incentivization of RO's vs LO's. The details (and this mechanism for that matter) can be subject to change.
            if not stepLimit.initialized and stepLimit.tickNext != None:
                if zeroForOne:
                    # -1 so it takes that limit order
                    nextLOatTick = stepLimit.tickNext - 1

                else:
                    nextLOatTick = stepLimit.tickNext

                nextLOatPrice = TickMath.getSqrtRatioAtTick(nextLOatTick)
            else:
                nextLOatPrice = sqrtPriceLimitX96

            ## compute values to swap to the target tick, price limit, or point where input#output amount is exhausted.
            if zeroForOne:
                sqrtRatioTargetX96 = max(
                    sqrtPriceLimitX96, step.sqrtPriceNextX96, nextLOatPrice
                )
            else:
                sqrtRatioTargetX96 = min(
                    sqrtPriceLimitX96, step.sqrtPriceNextX96, nextLOatPrice
                )

            # Continue the range order swap as normal
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
                self.ledger.transferToken(self, recipient, self.token1, abs(amount1))
            balanceBefore = self.balances[self.token0]
            self.ledger.transferToken(recipient, self, self.token0, abs(amount0))
            assert balanceBefore + abs(amount0) == self.balances[self.token0], "IIA"
        else:
            if amount0 < 0:
                self.ledger.transferToken(self, recipient, self.token0, abs(amount0))

            balanceBefore = self.balances[self.token1]
            self.ledger.transferToken(recipient, self, self.token1, abs(amount1))
            assert balanceBefore + abs(amount1) == self.balances[self.token1], "IIA"

        # Doing this at the end of the swap so we have recieved the tokens from the swap.
        # We could do this as a separate TX to get all the results of the positionBurning.
        for tick in state.ticksCrossed:
            self.burnCrossedPositions(
                ticksLimitMap, tick, self.token1 if zeroForOne else self.token0
            )

        return (
            recipient,
            amount0,
            amount1,
            state.sqrtPriceX96,
            state.liquidity,
            state.tick,
        )

    # Once we cross a tick, automatically burn all the positions that are in the tick.
    def burnCrossedPositions(self, tickLimitInfo, tick, token):
        checkInputTypes(string=(token), int24=(tick))
        assert tickLimitInfo[tick].oneMinusPercSwap == 0
        for owner in tickLimitInfo[tick].ownerPositions:
            # We should probably create a new burnLimit function for this to make it more efficient
            # e.g. that it burns position.liquidity instead of passing an amount.
            # For now just reusing it for simplicity.
            position, created = Position.getLimit(
                self.limitOrders, owner, tick, token == self.token0
            )
            # Health check
            assert not created
            # Health check - shouldn't be needed since burntPositions have automatically been collected
            # and removed, but just checking to make sure behaviour is correct.
            assert position.liquidity > 0
            # NOTE: We could implement a twist to the burnLimit function (or a combination of burn+collect)
            # that skips the decrement of tick liquidity and just burns the position. Then we burn the tick
            # separately at the end. This could save gas if we end up with this implementation.
            # Burn the entire order and collect tokens === remove position
            self.burnLimitOrder(token, owner, tick, position.liquidity)
            # NOTE: BurnLimitOrder will automatically call collectLimitOrder. That will clear the positions
            # and tick. Therefore we can check that the position has been burnt.
            Position.assertLimitPositionIsBurnt(
                self.limitOrders, owner, tick, token == self.token0
            )
        # Check that the tick has been cleared
        assert not tickLimitInfo.__contains__(tick)


# Return all the position keys (ticks) that have liquidity, as a sorted list.
def getKeysLimitTicksWithLiquidity(tickMapping):
    # NOTE: Right now we clear the positions (and therefore the tick) once a tick is fully swapped. Therefore,
    # we don't need to check for tick having liquidity (oneMinusPercSwap > 0). If that changes, we need to add
    # the "oneMinusPercSwap > 0" check back.

    # Dictionary with ticks that have oneMinusPercSwap > 0
    dictTicksWithLiq = {
        k: v
        for k, v in tickMapping.items()
        #     k: v for k, v in tickMapping.items() if tickMapping[k].oneMinusPercSwap > 0
    }
    # Return a list of sorted keys
    return sorted(list(dictTicksWithLiq.keys()))


# Find the next linearTick (all should have oneMinusPercSwap > 0) and pop them from the list. The input list
# should be a list of sorted keys.
def nextLimitTick(keysLimitTicks, lte, currentTick):
    checkInputTypes(bool=(lte), int24=(currentTick))

    # Only pop the value if tick will be used
    if lte:
        # Start from the most left
        if keysLimitTicks[0] <= currentTick:
            nextTick = keysLimitTicks.pop(0)
            return nextTick, True
        nextTick = keysLimitTicks[0]
    else:
        if keysLimitTicks[-1] > currentTick:
            # Start from the most right
            nextTick = keysLimitTicks.pop(-1)
            return nextTick, True
        nextTick = keysLimitTicks[-1]

    # If no tick with LO is found, then we're done - not modifying the keyList in case we can use
    # any of the ticks later in the swap, since current tick on the rangeOrder pool can change.
    # However, we return the next best tick so the range orders know (without popping)
    return nextTick, False
