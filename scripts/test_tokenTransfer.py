from Account import *
from utilities import *


def test_tokenTransfer():
    account0 = Account("ALICE", 100, 100)
    account1 = Account("BOB", 100, 100)

    # Token Transfer Test
    account0.balanceToken0 = 100
    account0.balanceToken1 = 100
    account1.balanceToken0 = 100
    account1.balanceToken1 = 100

    account0.transferTokens(account1, 25, 25)

    assert account0.balanceToken0 == 75
    assert account0.balanceToken1 == 75
    assert account1.balanceToken0 == 125
    assert account1.balanceToken1 == 125

    # Negative Amount
    tryExceptHandler(account0.transferTokens, "", account1, -25, 25)
    # Insufficient Balance
    tryExceptHandler(account0.transferTokens, "Insufficient balance", account1, 150, 25)

def test_tokenReceive():
    account0 = Account("ALICE", 100, 100)

    account0.receiveTokens(25, 25)
    assert account0.balanceToken0 == 125
    assert account0.balanceToken1 == 125

    account0.receiveTokens(0,0)
    assert account0.balanceToken0 == 125
    assert account0.balanceToken1 == 125

    tryExceptHandler(account0.receiveTokens, "", -25, 0)
    tryExceptHandler(account0.receiveTokens, "", 0, -25)
