import sys, os

sys.path.append(os.path.join(os.path.dirname(sys.path[0]), "tests"))
from utilities import *
import secrets

# For now this will only support the tokens that are initialized in the constructor function. Tranfering or receiving
# other tokens will fail (token not in balances dict).
class Account:
    def __init__(self, name, tokens, balances):
        checkInputTypes(string=(name, *tokens), uint256=(*balances,))
        assert len(tokens) == len(balances)
        # Check uniquness of tokens list
        assert len(set(tokens)) == len(tokens)

        self.name = name

        self.address = secrets.token_hex(40)

        self.tokens = tokens
        self.balances = {}

        # Assign initial balances
        for i in range(len(tokens)):
            self.balances[tokens[i]] = balances[i]

    def updateBalance(self, token, amount):
        checkInputTypes(string=(token), int256=(amount))
        self.balances[token] += amount

        # Check potential overflow/underflow that would happen in solidity
        checkUInt256(self.balances[token])


class Ledger:
    def __init__(self, initialAccounts):
        self.accounts = dict()
        for accountParams in initialAccounts:
            self.createAccount(accountParams[0], accountParams[1], accountParams[2])

    def createAccount(self, name, tokens, balances):
        account = Account(name, tokens, balances)
        assert not self.accounts.__contains__(account.address)
        self.accounts[account.address] = account

    # Add transfer and receive tokens functions
    def transferToken(self, sender, recipient, token, amount):
        checkInputTypes(account=(recipient), string=(token), uint256=(amount))

        if type(recipient) == str:
            recipient = self.getAccountWithAddress(recipient)
        if type(sender) == str:
            sender = self.getAccountWithAddress(sender)

        balanceSenderBefore = sender.balances[token]
        balanceReceiverBefore = recipient.balances[token]

        assert sender.balances[token] >= amount, "Insufficient balance"

        sender.updateBalance(token, -amount)

        self.receiveToken(recipient, token, amount)

        # Transfer health check
        assert sender.balances[token] == balanceSenderBefore - amount
        assert recipient.balances[token] == balanceReceiverBefore + amount

    def receiveToken(self, receiver, token, amount):
        checkInputTypes(string=(token), uint256=(amount))
        receiver.updateBalance(token, amount)

    def getAccountWithAddress(self, address):
        return self.accounts[address]

    def balanceOf(self, address, token):
        checkInputTypes(string=(address, token))
        return self.accounts[address].balances[token]
