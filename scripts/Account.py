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

        assert self.balances[token] >= amount, "Insufficient balance"

        self.balances[token] -= amount
        recipient.receiveToken(token, amount)

    def receiveToken(self, token, amount):
        checkInputTypes(string=(token), uint256=(amount))
        self.balances[token] += amount
