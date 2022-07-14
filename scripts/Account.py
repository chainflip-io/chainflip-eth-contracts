from scripts.utilities import checkUInt256


class Account:

    def __init__(self, name, tokens, balances):
        self.name = name
        assert len(tokens) == len(balances)
        # Check uniquness of tokens list
        assert len(set(tokens)) == len(tokens)
        self.tokens = tokens
        self.balances = {}
        for i in range(len(tokens)):
            checkUInt256(balances[i])
            self.balances[tokens[i]] = balances[i]

    # Add transfer and receive tokens functions
    def transferToken(self, recipient, token, amount):
        # Safeguard checks
        checkUInt256(amount)
        assert self.balances[token] >= amount, "Insufficient balance"

        self.balances[token] -= amount
        recipient.receiveToken(token, amount)

    def receiveToken(self, token, amount):
        checkUInt256(amount)
        # Safeguard check
        assert amount >= 0

        self.balances[token] += amount
