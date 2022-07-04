import sys
from os import path

import math

sys.path.append(path.abspath("scripts"))
from UniswapPool import *
import SwapMath as swapMath
import SqrtPriceMath


# ComputeSwapStep

def test_exactAmountIn_capped_notOneForZero():
    print('exact amount in that gets capped at price target in one for zero')
    price = encodePriceSqrt(1, 1)
    priceTarget = encodePriceSqrt(101, 100)
    liquidity = expandTo18Decimals(2)
    amount = expandTo18Decimals(1)
    fee = 600
    zeroForOne = False
    (sqrtQ, amountIn, amountOut, feeAmount) = swapMath.computeSwapStep(
        price,
        priceTarget,
        liquidity,
        amount,
        fee
      )

    # Original value == 9975124224178055
    assert int(amountIn) == 9975124224177900
    assert int(feeAmount) == 5988667735148
    # Original value == 9925619580021728
    assert int(amountOut) == 9925619580021576
    assert (amountIn + feeAmount) < amount, "Entire amount used"

    priceAfterWholeInputAmount = SqrtPriceMath.getNextSqrtPriceFromInput(
        price,
        liquidity,
        amount,
        zeroForOne
      )
    
    assert int(sqrtQ) == priceTarget, 'price not capped at price target'
    assert int(sqrtQ) < int(priceAfterWholeInputAmount), 'price not less than price after whole input amount'


def test_exactAmountOut_capped_notOneForZero():
    print('exact amount out that gets capped at price target in one for zero')
    price = encodePriceSqrt(1, 1)
    priceTarget = encodePriceSqrt(101, 100)
    liquidity = expandTo18Decimals(2)
    amount = expandTo18Decimals(1) * -1
    fee = 600
    zeroForOne = False

    (sqrtQ, amountIn, amountOut, feeAmount) = swapMath.computeSwapStep(
        price,
        priceTarget,
        liquidity,
        amount,
        fee
      )    

    # Original value == 9975124224178055
    assert int(amountIn) == 9975124224177900
    assert int(feeAmount) == 5988667735148
    # Original value == 9925619580021728
    assert int(amountOut) == 9925619580021576
    assert int(amountOut) < amount * -1 , 'entire amount out is not returned'

    priceAfterWholeOutputAmount = SqrtPriceMath.getNextSqrtPriceFromOutput(
        price,
        liquidity,
        amount * -1,
        zeroForOne
      )

    assert int(sqrtQ) == priceTarget, 'price is capped at price target'
    assert int(sqrtQ) < priceAfterWholeOutputAmount, 'price is less than price after whole output amount'


def test_exactAmount_fullySpent_notzeroForOne():
    print('exact amount in that is fully spent in one for zero')
    price = encodePriceSqrt(1, 1)
    priceTarget = encodePriceSqrt(1000, 100)
    liquidity = expandTo18Decimals(2)
    amount = expandTo18Decimals(1)
    fee = 600
    zeroForOne = False

    (sqrtQ, amountIn, amountOut, feeAmount) = SwapMath.computeSwapStep(
        price,
        priceTarget,
        liquidity,
        amount,
        fee
      )
    
    assert int(amountIn) == 999400000000000000
    assert int(feeAmount) == 600000000000000
    # Original value == 666399946655997866
    assert int(amountOut) == 666399946655997824
    assert (int(amountIn)+ int(feeAmount)) == amount, 'entire amount is used'

    print(type(feeAmount))
    priceAfterWholeInputAmountLessFee = SqrtPriceMath.getNextSqrtPriceFromInput(
        price,
        liquidity,
        amount - feeAmount,
        zeroForOne
      )

    assert int(sqrtQ) < priceTarget, 'price does not reach price target'
    assert int(sqrtQ) == int(priceAfterWholeInputAmountLessFee), 'price is equal to price after whole input amount'


def test_exactAmountOut_fullyReceived_notZeroForOne():
    print('exact amount out that is fully received in one for zero')
    price = encodePriceSqrt(1, 1)
    priceTarget = encodePriceSqrt(1000, 100)
    liquidity = expandTo18Decimals(2)
    amount = expandTo18Decimals(1) * -1
    fee = 600
    zeroForOne = False

    (sqrtQ, amountIn, amountOut, feeAmount) = SwapMath.computeSwapStep(
        price,
        priceTarget,
        liquidity,
        amount,
        fee
      )
    
    assert int(amountIn) == 2000000000000000000
    assert int(feeAmount) == 1200720432259356
    assert int(amountOut) == amount * -1

    priceAfterWholeOutputAmount = SqrtPriceMath.getNextSqrtPriceFromOutput(
        price,
        liquidity,
        amount * -1,
        zeroForOne
      )


    assert int(sqrtQ) < priceTarget, 'price does not reach price target'
    assert int(sqrtQ) == int(priceAfterWholeOutputAmount), 'price is equal to price after whole output amount'


def test_exactAmountOut_capped_amountOut():
    print("amount out is capped at the desired amount out")
    (sqrtQ, amountIn, amountOut, feeAmount) = swapMath.computeSwapStep(
        417332158212080721273783715441582,
        1452870262520218020823638996,
        159344665391607089467575320103,
        -1,
        1
      )

    assert int(amountIn) == 1
    assert int(feeAmount) == 1
    assert int(amountOut) == 1 ## would be 2 if not capped
    assert int(sqrtQ) == 417332158212080721273783715441581