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
class PositionLinearInfoSimple:
    isToken0: bool
    tickLower: int
    tickUpper: int
    owner: Account
    ## the amount of liquidity remaining to be swapped
    liquidityRemaining: int
    # to keep track of how much is swapped in case the position is burnt
    liquiditySwapped: int
    ## the fees owed to the position owner in the other token
    tokensOwed: int
    ## we need to keep track of the price if the position is partially swapped
    ## since we don't keep track of it at top level
    currentSqrtPricex96: int


class ChainflipPoolSimple(UniswapPool):
    def __init__(self, token0, token1, fee, tickSpacing):

        # Dictionary from tick to positions. Keys are ticks. For token0 positions we use TickLower for token1 positions we use TickUpper
        # Tick to list of positions
        self.positionsZero = {}
        self.positionsOne =  {}

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

        position = self._updatePositionLinearOrder(
            token,
            params.owner,
            params.tickLower,
            params.tickUpper,
            params.liquidityDelta,
        )

        # Initialize value
        amount = 0

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



        return (position, amount)
    
    # Used to mint and burn linear orders
    def _updatePositionLinearOrder(
        self, token, owner, tickLower, tickUpper, liquidityDelta
    ):
        checkInputTypes(
            string=token,
            accounts=(owner),
            int24=(tickLower, tickUpper),
            int128=(liquidityDelta),
        )
        # This will create a position if it doesn't exist
        positions =  self.positionsZero if token == self.token0 else self.positionsOne
        position = getLinearPositionSimple(
            positions, owner, tickLower, tickUpper, token == self.token0
        )

        # This should throw if we burn more than we have
        position.liquidityRemaining = LiquidityMath.addDelta(position.liquidityRemaining, liquidityDelta)

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
        positions =  self.positionsZero if token == self.token0 else self.positionsOne

        assertLimitPositionExistsSimple(
            positions, recipient, tickLower, tickUpper, token == self.token0
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

            positions = self.positionsOne if zeroForOne else self.positionsZero

            # FOR NOW ONLY SWAP LIMIT ORDERS

            while (
                state.amountSpecifiedRemaining != 0
                and state.sqrtPriceX96 != sqrtPriceLimitX96
            ):
                print("SWAP LOOP")
                print("current tick: " + str(state.tick))
                step = StepComputations(0, 0, 0, 0, 0, 0, 0)
                step.sqrtPriceStartX96 = state.sqrtPriceX96

                # This will return one of the ticks, there might be multiples or none
                # TODO: FIX PROBLEM HERE. We don't keep track of current liquidity when we mint so if we start
                # between two ticks we don't find any ticks. E.g. start at -23020, zeroForOne, only minted (-887220,22980)
                (position, step.initialized) = getNextPosition(
                    positions, state.tick, zeroForOne
                )
                print("position: " + str(position))

                if position == None:
                    # In this case we should be continuing to range orders or check next linear. For now we just add or decrease tick
                    # in search for a valid limit position to swap
                    #state.tick = (state.tick - 1) if zeroForOne else step.tickNext
                    state.tick = (state.tick - 1) if zeroForOne else (state.tick+1)
                    print("NO TICK FOUND")
                    #assert False
                    continue

                ## get the price for the next tick
                state.sqrtPriceX96 = position.currentSqrtPricex96

                # TODO: Check if direction is correct
                if zeroForOne:
                    step.sqrtPriceNextX96 = TickMath.getSqrtRatioAtTick(position.tickLower)
                    ## Add assertions to remember to check the direction
                    assert step.sqrtPriceNextX96 < step.sqrtPriceStartX96, "SPN"
                else:
                    step.sqrtPriceNextX96 = TickMath.getSqrtRatioAtTick(position.tickUpper)
                    assert step.sqrtPriceNextX96 > step.sqrtPriceStartX96, "SPN"
                
                #if position is partially swapped we need to load the currentPrice

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
                    position.liquidityRemaining,
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

                ## update position fee tracker
                if position.liquidityRemaining > 0:
                    state.feeGrowthGlobalX128 += mulDiv(
                        step.feeAmount, FixedPoint128_Q128, position.liquidityRemaining
                    )
                    # Addition can overflow in Solidity - mimic it
                    state.feeGrowthGlobalX128 = toUint256(state.feeGrowthGlobalX128)

                ## shift tick if we reached the next price
                if state.sqrtPriceX96 == step.sqrtPriceNextX96:
                    ## if the tick is initialized, run the tick transition
                    ## @dev: here is where we should handle the case of an uninitialized boundary tick
                    if step.initialized:
                        # TODO: Burn position and calculate fees - leave it ready for collect (or also collect?!)
                        position.liquidityRemaining = 0
                        
                    # DO NOT move the tick for now since there might be multiple positions in the same tick
                    #state.tick = (step.tickNext - 1) if zeroForOne else step.tickNext
                elif state.sqrtPriceX96 != step.sqrtPriceStartX96:
                    ## recompute unless we're on a lower tick boundary (i.e. already transitioned ticks), and haven't moved
                    # DO NOT move the tick for now since there might be multiple positions in the same tick
                    state.tick = TickMath.getTickAtSqrtRatio(state.sqrtPriceX96)
                    # Store in the position the latest price swapped
                    position.currentSqrtPriceX96 = state.sqrtPriceX96

            ## End of swap loop
            ## update tick

            # TODO: This will probably need to change, since it should only change it if range orders change it.
            if state.tick != slot0Start.tick:
                self.slot0.sqrtPriceX96 = state.sqrtPriceX96
                self.slot0.tick = state.tick
            else:
                ## otherwise just update the price
                self.slot0.sqrtPriceX96 = state.sqrtPriceX96


            ## update fee growth global and, if necessary, protocol fees
            ## overflow is acceptable, protocol has to withdraw before it hits type(uint128).max fees

            if zeroForOne:
                if state.protocolFee > 0:
                    self.protocolFees.token0 += state.protocolFee
            else:
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
                0,
                state.tick,
            )


def getLinearPositionSimple(listPositions, owner, tickLower, tickUpper, isToken0):
    checkInputTypes(account=owner, int24=(tickLower, tickLower))

    # Need to handle non-existing positions in Python
    if isToken0:
        key = tickUpper
    else:
        key = tickLower

    if not listPositions.__contains__(key):
        # We don't want to create a new position if it doesn't exist!
        # In the case of collect we add an assert after that so it reverts.
        # For mint there is an amount > 0 check so it is OK to initialize
        # In burn if the position is not initialized, when calling Position.update it will revert with "NP"
        listPositions[key] = []
        if isToken0:
            listPositions[key].append(PositionLinearInfoSimple(isToken0,tickLower,tickUpper,owner,0,0,0,TickMath.getSqrtRatioAtTick(tickLower)))
        else:
            listPositions[key].append(PositionLinearInfoSimple(isToken0,tickLower,tickUpper,owner,0,0,0,TickMath.getSqrtRatioAtTick(tickUpper)))

        return listPositions[key][-1]

    # If there are values at that tickKey:
    positionsAtTick = listPositions[key]

    for i in range(len(positionsAtTick)):
        #No need to check isToken0 in theory
        if positionsAtTick[i].isToken0 == isToken0 and positionsAtTick[i].tickLower == tickLower and positionsAtTick[i].tickUpper == tickUpper and positionsAtTick[i].owner == owner:
            return positionsAtTick[i]

    # If position not found on that tick, create a new one
    if isToken0:
        positionsAtTick.append(PositionLinearInfoSimple(isToken0,tickLower,tickUpper,owner,0,0,0,TickMath.getSqrtRatioAtTick(tickLower)))
    else:
        positionsAtTick.append(PositionLinearInfoSimple(isToken0,tickLower,tickUpper,owner,0,0,0,TickMath.getSqrtRatioAtTick(tickUpper)))
    
    return listPositions[key][-1]





# def getNextPosition(listPositions,tick, zeroForOne):
#     # Get the next initialized Linear position
#     # Ideally it would be bundled into a tick and do a big swap. To make it easy in python we just grab the next initialized
#     # position and swap position by position.

#     # TODO.: Find the first tick that is initialized and that matches the swapping requirements. For now regardless of how large or
#     # wide the position is. 
#     for i in range(len(listPositions)):
#         # TODO: Check if direction is correct
#         if zeroForOne:
#             # If zeroForOne
#             if not listPositions[i].isToken0 and listPositions[i].tickUpper == tick and listPositions[i].liquidityRemaining > 0:
#                 return (listPositions[i], True)
#         else:
#             if listPositions[i].isToken0 and listPositions[i].tickLower == tick and listPositions[i].liquidityRemaining > 0:
#                 return (listPositions[i], True)
#     return (None, True)


def getNextPosition(positionsMap, tick, lte):
    checkInputTypes(int24=(tick), bool=(lte))

    if not positionsMap.__contains__(tick):
        # If tick doesn't exist in the mapping we fake it (easier than searching for nearest value)
        sortedKeyList = sorted(list(positionsMap.keys()) + [tick])
    else:
        sortedKeyList = sorted(list(positionsMap.keys()))

    indexCurrentTick = sortedKeyList.index(tick)

    #TODO: We need to swap how we store LinearOrder 0 and 1 (tickUpper/Lower for this to work). So we look at HighTick
    if lte:
        # If the current tick is initialized (not faked), we return the current tick
        if positionsMap.__contains__(tick):
                return positionsMap[tick], True
        elif indexCurrentTick == 0:
            # No tick to the left
            return None, False
        else:
            while (indexCurrentTick > 0):
                nextTick = sortedKeyList[indexCurrentTick - 1]
                for i in range(len(positionsMap[nextTick])):
                    if positionsMap[nextTick][i].liquidityRemaining > 0:
                        # Return the first position that has tick Lower to the left of the current tick
                        return (positionsMap[nextTick][i], True)
                # If none of the positions match what we are looking for, we look for next tick again
                indexCurrentTick -= 1
            # No more ticks nor positions to the left
            return None, False
    else:
    #TODO: We need to swap how we store LinearOrder 0 and 1 (tickUpper/Lower for this to work). So we look at LowTick
        # THis first case might be wrong
        if positionsMap.__contains__(tick):
                return positionsMap[tick], True
        elif indexCurrentTick == len(sortedKeyList) - 1:
            # No tick to the right
            return None, False
        else:
            while (indexCurrentTick <  len(sortedKeyList)):
                nextTick = sortedKeyList[indexCurrentTick - 1]
                for i in range(len(positionsMap[nextTick])):
                    if positionsMap[nextTick][i].liquidityRemaining > 0:
                        # Return the first position that has tick Lower to the left of the current tick
                        return (positionsMap[nextTick][i], True)
                # If none of the positions match what we are looking for, we look for next tick again
                indexCurrentTick += 1
            # No more ticks nor positions to the right
            return None, False













    # if not positionsMap.__contains__(tick):
    #     # If there are no positions at that tick we fake it (easier than searching for nearest value)
    #     sortedKeyList = sorted(list(positionsMap.keys()) + [tick])
    # else:
    #     sortedKeyList = sorted(list(positionsMap.keys()))

    # indexCurrentTick = sortedKeyList.index(tick)

    if not positionsMap.__contains__(tick):
        # TODO: Improve this depending on how to decide between range orders and limit orders
        return None, False

    # Return the first position that is has liquidityRemaining >0. The direction should be correct.
    for i in range(len(positionsMap)):
        if positionsMap[i].liquidityRemaining > 0:
            return positionsMap[tick][0]
    return None, False


    # if lte:
    #     # If the current tick is initialized (not faked), we return the current tick
    #     if positionsMap.__contains__(tick):
    #         return tick, True
    #     elif indexCurrentTick == 0:
    #         # No tick to the left
    #         return None, False
    #     else:
    #         nextTick = sortedKeyList[indexCurrentTick - 1]
    # else:

    #     if indexCurrentTick == len(sortedKeyList) - 1:
    #         # No tick to the right
    #         return None, False
    #     nextTick = sortedKeyList[indexCurrentTick + 1]

    # # Return tick within the boundaries
    # return nextTick, True


def assertLimitPositionExistsSimple(self, owner, tickLower, tickUpper, isToken0):
    checkInputTypes(account=owner, int24=(tickLower, tickLower))
    positionInfo = getLinearPositionSimple(self, owner, tickLower, tickUpper, isToken0)
    if isToken0:
        assert positionInfo != PositionLinearInfoSimple(isToken0,tickLower,tickUpper,owner,0,0,0,TickMath.getSqrtRatioAtTick(tickLower)), "Position doesn't exist"
    else:
        assert positionInfo != PositionLinearInfoSimple(isToken0,tickLower,tickUpper,owner,0,0,0,TickMath.getSqrtRatioAtTick(tickUpper)), "Position doesn't exist"


# Helper for tests
def assertLimitPositionNotExistsSimple(self, owner, tickLower, tickUpper, isToken0):
    checkInputTypes(account=owner, int24=(tickLower, tickLower))
    positionInfo = getLinearPositionSimple(self, owner, tickLower, tickUpper, isToken0)
    if isToken0:
        assert positionInfo == PositionLinearInfoSimple(isToken0,tickLower,tickUpper,owner,0,0,0,TickMath.getSqrtRatioAtTick(tickLower)), "Position doesn't exist"
    else:
        assert positionInfo == PositionLinearInfoSimple(isToken0,tickLower,tickUpper,owner,0,0,0,TickMath.getSqrtRatioAtTick(tickUpper)), "Position doesn't exist"
