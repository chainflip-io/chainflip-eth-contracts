import sys, os

sys.path.append(os.path.join(os.path.dirname(sys.path[0]), "tests"))
from utilities import *

# For now this will only support the tokens that are initialized in the constructor function. Tranfering or receiving
# other tokens will fail (token not in balances dict).
class Account:
    def __init__(self, name, tokens, balances):
        checkInputTypes(string=(name, *tokens), uint256=(*balances,))
        assert len(tokens) == len(balances)
        # Check uniquness of tokens list
        assert len(set(tokens)) == len(tokens)

        self.name = name
        self.tokens = tokens
        self.balances = {}

        # Assign initial balances
        for i in range(len(tokens)):
            self.balances[tokens[i]] = balances[i]

    # Add transfer and receive tokens functions
    def transferToken(self, recipient, token, amount):
        checkInputTypes(account=(recipient), string=(token), uint256=(amount))

        balanceSenderBefore = self.balances[token]
        balanceReceiverBefore = recipient.balances[token]

        assert self.balances[token] >= amount, "Insufficient balance"

        self.updateBalance(token, -amount)

        recipient.receiveToken(token, amount)

        # Transfer health check
        assert self.balances[token] == balanceSenderBefore - amount
        assert recipient.balances[token] == balanceReceiverBefore + amount

    def receiveToken(self, token, amount):
        checkInputTypes(string=(token), uint256=(amount))
        self.updateBalance(token, amount)

    def updateBalance(self, token, amount):
        checkInputTypes(string=(token), int256=(amount))
        self.balances[token] += amount

        # Check potential overflow/underflow that would happen in solidity
        checkUInt256(self.balances[token])
