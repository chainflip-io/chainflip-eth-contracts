from Account import *
from utilities import *


def test_tokenTransfer():
    account0 = Account("ALICE",TEST_TOKENS, [100, 100])
    account1 = Account("BOB", TEST_TOKENS, [100, 100])

    # Token Transfer Test
    account0.balances[TEST_TOKENS[0]] = 100
    account0.balances[TEST_TOKENS[1]] = 100
    account1.balances[TEST_TOKENS[0]] = 100
    account1.balances[TEST_TOKENS[1]] = 100

    account0.transferToken(account1,TEST_TOKENS[0], 25)

    assert account0.balances[TEST_TOKENS[0]] == 75
    assert account0.balances[TEST_TOKENS[1]] == 100
    assert account1.balances[TEST_TOKENS[0]] == 125
    assert account1.balances[TEST_TOKENS[1]] == 100

    # Negative Amount
    tryExceptHandler(account0.transferToken, "", account1, TEST_TOKENS[0], -25)
    tryExceptHandler(account0.transferToken, "", account1, TEST_TOKENS[1], -25)

    # Insufficient Balance
    tryExceptHandler(account0.transferToken, "Insufficient balance", account1,TEST_TOKENS[0], 150)

def test_tokenReceive():
    account0 = Account("ALICE", TEST_TOKENS, [100, 100])

    account0.receiveToken(TEST_TOKENS[0], 25)
    assert account0.balances[TEST_TOKENS[0]] == 125
    assert account0.balances[TEST_TOKENS[1]] == 100

    account0.receiveToken(TEST_TOKENS[0],0)
    assert account0.balances[TEST_TOKENS[0]] == 125
    assert account0.balances[TEST_TOKENS[1]] == 100

    account0.receiveToken(TEST_TOKENS[1],13)
    assert account0.balances[TEST_TOKENS[0]] == 125
    assert account0.balances[TEST_TOKENS[1]] == 113

    tryExceptHandler(account0.receiveToken, "", TEST_TOKENS[0], -25)
    tryExceptHandler(account0.receiveToken, "", TEST_TOKENS[1], -25)
