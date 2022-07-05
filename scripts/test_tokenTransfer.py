from UniswapPool import *
from utilities import *

def test_tokenTransfer():
    pool0 = UniswapPool(1, 2)
    pool1 = UniswapPool(2, 3)

    # Token Transfer Test
    pool0.balanceToken0 = 100
    pool0.balanceToken1 = 100
    pool1.balanceToken0 = 100
    pool1.balanceToken1 = 100

    pool0.transferTokens(pool1, 25, 25)

    assert pool0.balanceToken0 == 75
    assert pool0.balanceToken1 == 75
    assert pool1.balanceToken0 == 125
    assert pool1.balanceToken1 == 125

    # Negative Amount
    tryExceptHandler(pool0.transferTokens, "", pool1, -25, 25)
    # Insufficient Balance
    tryExceptHandler(pool0.transferTokens, "Insufficient balance", pool1, 150, 25)
